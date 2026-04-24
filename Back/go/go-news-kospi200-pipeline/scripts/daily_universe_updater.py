import json
import shutil
import sys
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

from pykrx import stock


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_UNIVERSE_CURRENT = PROJECT_ROOT / "data" / "universe" / "current"
DATA_UNIVERSE_ARCHIVE = PROJECT_ROOT / "data" / "universe" / "archive"
DATA_UNIVERSE_ARCHIVE_MONTHLY = PROJECT_ROOT / "data" / "universe" / "archive-monthly"
LOG_DIR = PROJECT_ROOT / "logs" / "universe"

RETENTION_DAYS = 30
KOSPI200_INDEX_CODE = "1028"  # KOSPI200


@dataclass
class Constituent:
    ticker: str
    company_name_ko: str
    market: str = "KOSPI"
    is_active: bool = True


@dataclass
class AliasEntry:
    ticker: str
    company_name_ko: str
    company_name_en: str
    market: str
    aliases: List[str]
    negative_aliases: List[str]
    search_queries: List[str]
    is_active: bool
    match_priority: int
    notes: str


def ensure_dirs() -> None:
    DATA_UNIVERSE_CURRENT.mkdir(parents=True, exist_ok=True)
    DATA_UNIVERSE_ARCHIVE.mkdir(parents=True, exist_ok=True)
    DATA_UNIVERSE_ARCHIVE_MONTHLY.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def now_local() -> datetime:
    return datetime.now()


def today_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def month_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def uniq_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        v = item.strip()
        if not v:
            continue
        if v in seen:
            continue
        seen.add(v)
        result.append(v)
    return result


def current_files_exist() -> bool:
    required = [
        DATA_UNIVERSE_CURRENT / "kospi200.constituents.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.aliases.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.match_rules.current.json",
    ]
    return all(p.exists() for p in required)


def load_existing_constituent_count() -> int:
    path = DATA_UNIVERSE_CURRENT / "kospi200.constituents.current.json"
    if not path.exists():
        return 0
    try:
        data = read_json(path)
        return len(data.get("companies", []))
    except Exception:
        return 0


def build_company_name_en(company_name_ko: str) -> str:
    # 1차 자동 생성기에서는 영문명을 공란으로 두고,
    # 필요 종목만 수동 보강한다.
    return ""


def build_negative_aliases(company_name_ko: str) -> List[str]:
    rules = {
        "기아": [
            "기아대책",
            "KIA 타이거즈",
            "기아 타이거즈",
            "마운드",
            "선발",
            "타선",
            "불펜",
            "개막 시리즈",
            "챔피언스필드",
            "챔피언스 필드",
        ],
        "NAVER": [
            "Naver Blog",
            "네이버 블로그",
        ],
    }
    return rules.get(company_name_ko, [])


def build_aliases(company_name_ko: str, ticker: str) -> List[str]:
    base = [company_name_ko, ticker]

    extra_map = {
        "삼성전자": ["Samsung Electronics"],
        "SK하이닉스": ["SK hynix"],
        "현대차": ["현대자동차"],
        "NAVER": ["네이버", "Naver"],
        "LG에너지솔루션": ["LG엔솔", "LG Energy Solution"],
        "셀트리온": ["Celltrion"],
        "기아": ["Kia Corporation", "Kia Motors"],
    }

    aliases = base + extra_map.get(company_name_ko, [])
    return uniq_keep_order(aliases)


def build_search_queries(company_name_ko: str, aliases: List[str]) -> List[str]:
    queries = [company_name_ko]

    query_map = {
        "삼성전자": ["삼성전자 반도체", "삼성전자 실적"],
        "SK하이닉스": ["SK하이닉스 HBM", "SK하이닉스 실적"],
        "현대차": ["현대차 실적", "현대자동차"],
        "NAVER": ["NAVER 실적", "네이버", "Naver"],
        "LG에너지솔루션": ["LG엔솔", "LG에너지솔루션 배터리"],
        "셀트리온": ["셀트리온 실적", "셀트리온 바이오시밀러"],
        "기아": ["기아 실적", "기아 전기차", "Kia Corporation"],
    }

    queries.extend(query_map.get(company_name_ko, []))
    queries.extend([a for a in aliases if a != company_name_ko and len(a) >= 4])

    return uniq_keep_order(queries)


def build_match_rules(as_of_date: str) -> dict:
    return {
        "index_name": "KOSPI200",
        "as_of_date": as_of_date,
        "global_negative_tokens": [
            "SK", "LG", "CJ", "한화", "두산", "현대", "삼성", "LS", "DL"
        ],
        "weak_ascii_aliases": [
            "DL", "LS", "CJ", "LG", "GS", "KT", "HMM", "GKL", "KCC", "SK", "SKC", "F&F"
        ],
        "exact_token_aliases": [
            "기아"
        ],
        "min_alias_length": 2,
        "disallow_group_name_only_match": True,
        "prefer_exact_company_name": True,
        "prefer_ticker_match": True,
        "remove_source_name_from_snippet": True,
        "normalize_separators": ["ㆍ", "·", "•", "∙"],
        "notes": "단독 그룹명 오탐 억제, 구분자 정규화 포함"
    }


def fetch_kospi200_constituents() -> Tuple[List[Constituent], List[str]]:
    """
    pykrx로 코스피200 구성종목을 조회한다.
    pykrx/원천 응답이 비정상일 때 빈 리스트를 반환하고,
    호출부에서 fallback 처리한다.
    """
    debug_logs: List[str] = []

    try:
        tickers = stock.get_index_portfolio_deposit_file(KOSPI200_INDEX_CODE)
        debug_logs.append(f"[INFO] raw index tickers fetched count={len(tickers)}")
    except Exception as e:
        debug_logs.append(f"[WARN] get_index_portfolio_deposit_file failed: {type(e).__name__}: {e}")
        return [], debug_logs

    constituents: List[Constituent] = []
    for ticker in tickers:
        try:
            name = stock.get_market_ticker_name(ticker)
        except Exception as e:
            debug_logs.append(f"[WARN] get_market_ticker_name failed for {ticker}: {type(e).__name__}: {e}")
            continue

        if not name:
            debug_logs.append(f"[WARN] empty company name for ticker={ticker}")
            continue

        constituents.append(
            Constituent(
                ticker=ticker,
                company_name_ko=name,
                market="KOSPI",
                is_active=True,
            )
        )

    constituents.sort(key=lambda x: x.ticker)
    debug_logs.append(f"[INFO] resolved constituent names count={len(constituents)}")
    return constituents, debug_logs


def build_constituents_json(as_of_date: str, constituents: List[Constituent]) -> dict:
    return {
        "index_name": "KOSPI200",
        "as_of_date": as_of_date,
        "source": {
            "provider": "pykrx",
            "index_code": KOSPI200_INDEX_CODE,
            "description": "KOSPI200 constituents fetched via pykrx"
        },
        "companies": [asdict(c) for c in constituents],
    }


def build_aliases_json(as_of_date: str, constituents: List[Constituent]) -> dict:
    companies: List[dict] = []

    for c in constituents:
        aliases = build_aliases(c.company_name_ko, c.ticker)
        entry = AliasEntry(
            ticker=c.ticker,
            company_name_ko=c.company_name_ko,
            company_name_en=build_company_name_en(c.company_name_ko),
            market=c.market,
            aliases=aliases,
            negative_aliases=build_negative_aliases(c.company_name_ko),
            search_queries=build_search_queries(c.company_name_ko, aliases),
            is_active=True,
            match_priority=100,
            notes="auto-generated by daily_universe_updater.py",
        )
        companies.append(asdict(entry))

    return {
        "index_name": "KOSPI200",
        "as_of_date": as_of_date,
        "source": {
            "provider": "pykrx",
            "index_code": KOSPI200_INDEX_CODE,
            "description": "Auto-generated alias dictionary for KOSPI200"
        },
        "companies": companies,
    }


def archive_current_files(as_of_date: str):
    archive_dir = DATA_UNIVERSE_ARCHIVE / as_of_date
    archive_dir.mkdir(parents=True, exist_ok=True)

    current_files = [
        DATA_UNIVERSE_CURRENT / "kospi200.constituents.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.aliases.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.match_rules.current.json",
    ]

    copied = []
    for src in current_files:
        if src.exists():
            dst = archive_dir / src.name.replace(".current", f".{as_of_date}")
            safe_copy(src, dst)
            copied.append(dst)

    return copied


def archive_monthly_snapshot(dt: datetime):
    month_folder = DATA_UNIVERSE_ARCHIVE_MONTHLY / month_str(dt)
    month_folder.mkdir(parents=True, exist_ok=True)

    as_of_date = today_str(dt)
    current_files = [
        DATA_UNIVERSE_CURRENT / "kospi200.constituents.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.aliases.current.json",
        DATA_UNIVERSE_CURRENT / "kospi200.match_rules.current.json",
    ]

    copied = []
    for src in current_files:
        if src.exists():
            dst = month_folder / src.name.replace(".current", f".{as_of_date}")
            safe_copy(src, dst)
            copied.append(dst)

    return copied


def cleanup_old_daily_archives(dt: datetime):
    cutoff = dt.date() - timedelta(days=RETENTION_DAYS)
    deleted = []

    for child in DATA_UNIVERSE_ARCHIVE.iterdir():
        if not child.is_dir():
            continue
        try:
            folder_date = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            continue

        if folder_date < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            deleted.append(child.name)

    return deleted


def write_log(log_lines, dt: datetime) -> Path:
    log_path = LOG_DIR / f"{today_str(dt)}.log"
    with log_path.open("a", encoding="utf-8") as f:
        for line in log_lines:
            f.write(line + "\n")
    return log_path


def main() -> int:
    ensure_dirs()
    dt = now_local()
    as_of_date = today_str(dt)

    log_lines = [f"[START] daily_universe_updater at {dt.isoformat()}"]

    try:
        constituents, fetch_logs = fetch_kospi200_constituents()
        log_lines.extend(fetch_logs)
        log_lines.append(f"[INFO] fetched constituents count={len(constituents)}")

        if len(constituents) == 0:
            existing_count = load_existing_constituent_count()
            if current_files_exist() and existing_count > 0:
                log_lines.append("[WARN] pykrx fetch returned no constituents; keeping existing current files")
                log_lines.append(f"[WARN] existing current constituent count={existing_count}")
                log_lines.append("[SUCCESS] updater skipped refresh but preserved existing current files")
                log_path = write_log(log_lines, dt)
                print("daily_universe_updater completed with fallback (existing current files preserved)")
                print(f"log written to: {log_path}")
                return 0

            raise RuntimeError(
                "No KOSPI200 constituents fetched from pykrx, and no existing current files are available."
            )

        constituents_json = build_constituents_json(as_of_date, constituents)
        aliases_json = build_aliases_json(as_of_date, constituents)

        match_rules_path = DATA_UNIVERSE_CURRENT / "kospi200.match_rules.current.json"
        if match_rules_path.exists():
            match_rules_json = read_json(match_rules_path)
            match_rules_json["as_of_date"] = as_of_date
            log_lines.append("[INFO] existing match_rules.current.json loaded and as_of_date updated")
        else:
            match_rules_json = build_match_rules(as_of_date)
            log_lines.append("[INFO] match_rules.current.json did not exist, created default")

        write_json(DATA_UNIVERSE_CURRENT / "kospi200.constituents.current.json", constituents_json)
        write_json(DATA_UNIVERSE_CURRENT / "kospi200.aliases.current.json", aliases_json)
        write_json(match_rules_path, match_rules_json)
        log_lines.append("[INFO] current universe files written")

        archived = archive_current_files(as_of_date)
        log_lines.append(f"[INFO] daily archive written files={len(archived)}")

        if dt.day == 1:
            monthly = archive_monthly_snapshot(dt)
            log_lines.append(f"[INFO] monthly snapshot written files={len(monthly)}")
        else:
            log_lines.append("[INFO] monthly snapshot skipped (not first day of month)")

        deleted = cleanup_old_daily_archives(dt)
        log_lines.append(f"[INFO] deleted old daily archives count={len(deleted)}")
        if deleted:
            log_lines.append(f"[INFO] deleted folders={deleted}")

        sample_names = [c.company_name_ko for c in constituents[:10]]
        log_lines.append(f"[INFO] first_10_companies={sample_names}")
        log_lines.append("[SUCCESS] daily_universe_updater completed successfully")

    except Exception as e:
        log_lines.append(f"[ERROR] {type(e).__name__}: {e}")
        log_lines.append(traceback.format_exc())
        log_path = write_log(log_lines, dt)
        print(f"daily_universe_updater failed: {e}")
        print(f"log written to: {log_path}")
        return 1

    log_path = write_log(log_lines, dt)
    print("daily_universe_updater completed successfully")
    print(f"log written to: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
