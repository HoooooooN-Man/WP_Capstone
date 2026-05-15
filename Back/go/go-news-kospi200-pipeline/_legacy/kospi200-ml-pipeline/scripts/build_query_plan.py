
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ALIASES_PATH = PROJECT_ROOT / "data" / "universe" / "current" / "kospi200.aliases.current.json"
MATCH_RULES_PATH = PROJECT_ROOT / "data" / "universe" / "current" / "kospi200.match_rules.current.json"

PLANS_DAILY_DIR = PROJECT_ROOT / "data" / "plans" / "daily"
PLANS_CURRENT_DIR = PROJECT_ROOT / "data" / "plans" / "current"
LOG_DIR = PROJECT_ROOT / "logs" / "planner"

DEFAULT_MAX_QUERIES_PER_COMPANY = 3
DEFAULT_MAX_RESULTS_HINT = 100
DEFAULT_MACRO_QUERIES = ["반도체", "금리", "환율", "코스피"]


def ensure_dirs() -> None:
    PLANS_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    PLANS_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_log(lines: List[str], as_of_date: str) -> Path:
    log_path = LOG_DIR / f"{as_of_date}.log"
    with log_path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return log_path


def normalize_text(value: str, separators: List[str]) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    for ch in separators:
        s = s.replace(ch, " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def uniq_keep_order(items: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen = set()
    result = []
    for value, source in items:
        if value in seen:
            continue
        seen.add(value)
        result.append((value, source))
    return result


def is_pure_ticker(query: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", query))


def is_short_ascii_token(query: str) -> bool:
    q = query.strip()
    return len(q) <= 3 and all(ord(c) < 128 for c in q)


def load_match_rules() -> dict:
    if MATCH_RULES_PATH.exists():
        return read_json(MATCH_RULES_PATH)
    return {
        "weak_ascii_aliases": ["DL", "LS", "CJ", "LG", "GS", "KT", "HMM", "GKL", "KCC", "SK", "SKC", "F&F"],
        "global_negative_tokens": ["SK", "LG", "CJ", "한화", "두산", "현대", "삼성", "LS", "DL"],
        "normalize_separators": ["ㆍ", "·", "•", "∙"],
    }


def build_company_queries(company: dict, rules: dict, max_queries_per_company: int) -> List[dict]:
    company_name_ko = str(company.get("company_name_ko", "")).strip()
    company_name_en = str(company.get("company_name_en", "")).strip()
    aliases = company.get("aliases", []) or []
    search_queries = company.get("search_queries", []) or []

    separators = rules.get("normalize_separators", ["ㆍ", "·", "•", "∙"])
    weak_ascii_aliases = set(rules.get("weak_ascii_aliases", []))
    global_negative_tokens = set(rules.get("global_negative_tokens", []))

    candidates: List[Tuple[str, str]] = []
    if company_name_ko:
        candidates.append((normalize_text(company_name_ko, separators), "company_name_ko"))
    if company_name_en:
        candidates.append((normalize_text(company_name_en, separators), "company_name_en"))
    for q in search_queries:
        candidates.append((normalize_text(q, separators), "search_query"))
    for a in aliases:
        candidates.append((normalize_text(a, separators), "alias"))

    candidates = uniq_keep_order(candidates)

    selected: List[dict] = []
    seen = set()
    primary_allow = {
        normalize_text(company_name_ko, separators),
        normalize_text(company_name_en, separators) if company_name_en else "",
    }

    for q, source in candidates:
        if not q or q in seen or is_pure_ticker(q):
            continue
        if q not in primary_allow:
            if q in weak_ascii_aliases:
                continue
            if q in global_negative_tokens:
                continue
            if is_short_ascii_token(q):
                continue
        seen.add(q)
        selected.append({"query": q, "query_source": source})
        if len(selected) >= max_queries_per_company:
            break

    if not selected and company_name_ko:
        selected.append({"query": normalize_text(company_name_ko, separators), "query_source": "company_name_ko_fallback"})
    return selected


def build_jobs(alias_data: dict, match_rules: dict, max_queries_per_company: int, include_macro: bool):
    log_lines: List[str] = []
    jobs: List[dict] = []
    companies = alias_data.get("companies", []) or []
    log_lines.append(f"[INFO] alias companies loaded count={len(companies)}")

    company_job_count = 0
    for company in companies:
        if not company.get("is_active", True):
            continue
        ticker = str(company.get("ticker", "")).strip()
        company_name_ko = str(company.get("company_name_ko", "")).strip()
        market = str(company.get("market", "KOSPI")).strip()
        priority = int(company.get("match_priority", 100))
        query_items = build_company_queries(company, match_rules, max_queries_per_company)
        if not query_items:
            log_lines.append(f"[WARN] no query built for ticker={ticker} company={company_name_ko}")
            continue
        for idx, q in enumerate(query_items, start=1):
            jobs.append({
                "job_id": f"{ticker}-{idx:02d}",
                "job_type": "company",
                "ticker": ticker,
                "company_name_ko": company_name_ko,
                "market": market,
                "priority": priority,
                "query": q["query"],
                "query_source": q["query_source"],
                "query_rank": idx,
                "query_group_size": len(query_items),
                "max_results_hint": DEFAULT_MAX_RESULTS_HINT,
                "used_for_ml": True,
                "used_for_digest": True,
            })
            company_job_count += 1

    macro_job_count = 0
    if include_macro:
        for idx, macro_q in enumerate(DEFAULT_MACRO_QUERIES, start=1):
            jobs.append({
                "job_id": f"macro-{idx:02d}",
                "job_type": "macro",
                "ticker": "",
                "company_name_ko": "",
                "market": "KOSPI",
                "priority": 50,
                "query": macro_q,
                "query_source": "macro_default",
                "query_rank": idx,
                "query_group_size": len(DEFAULT_MACRO_QUERIES),
                "max_results_hint": DEFAULT_MAX_RESULTS_HINT,
                "used_for_ml": False,
                "used_for_digest": True,
            })
            macro_job_count += 1

    log_lines.append(f"[INFO] company jobs built count={company_job_count}")
    log_lines.append(f"[INFO] macro jobs built count={macro_job_count}")
    log_lines.append(f"[INFO] total jobs built count={len(jobs)}")
    return jobs, log_lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Build daily query plan for KOSPI200 fan-out crawling")
    parser.add_argument("--date", dest="as_of_date", default=datetime.now().strftime("%Y-%m-%d"), help="Plan date in YYYY-MM-DD")
    parser.add_argument("--max-queries-per-company", type=int, default=DEFAULT_MAX_QUERIES_PER_COMPANY, help="Max queries per company")
    parser.add_argument("--no-macro", action="store_true", help="Exclude macro queries")
    args = parser.parse_args()

    ensure_dirs()
    as_of_date = args.as_of_date
    generated_at = datetime.now().isoformat()
    include_macro = not args.no_macro

    log_lines: List[str] = []
    log_lines.append(f"[START] build_query_plan at {generated_at}")
    log_lines.append(f"[INFO] as_of_date={as_of_date}")
    log_lines.append(f"[INFO] max_queries_per_company={args.max_queries_per_company}")
    log_lines.append(f"[INFO] include_macro={include_macro}")

    try:
        if not ALIASES_PATH.exists():
            raise FileNotFoundError(f"aliases file not found: {ALIASES_PATH}")
        alias_data = read_json(ALIASES_PATH)
        match_rules = load_match_rules()
        jobs, build_logs = build_jobs(alias_data, match_rules, args.max_queries_per_company, include_macro)
        log_lines.extend(build_logs)

        company_count = len(alias_data.get("companies", []) or [])
        company_jobs = [j for j in jobs if j["job_type"] == "company"]
        macro_jobs = [j for j in jobs if j["job_type"] == "macro"]

        plan = {
            "plan_name": "KOSPI200_DAILY_QUERY_PLAN",
            "as_of_date": as_of_date,
            "generated_at": generated_at,
            "source_files": {
                "aliases_path": str(ALIASES_PATH),
                "match_rules_path": str(MATCH_RULES_PATH),
            },
            "stats": {
                "company_count": company_count,
                "company_job_count": len(company_jobs),
                "macro_job_count": len(macro_jobs),
                "total_job_count": len(jobs),
                "max_queries_per_company": args.max_queries_per_company,
            },
            "jobs": jobs,
        }

        dated_plan_path = PLANS_DAILY_DIR / f"query-plan-{as_of_date}.json"
        current_plan_path = PLANS_CURRENT_DIR / "query-plan.current.json"
        write_json(dated_plan_path, plan)
        write_json(current_plan_path, plan)

        log_lines.append(f"[INFO] dated plan written to {dated_plan_path}")
        log_lines.append(f"[INFO] current plan written to {current_plan_path}")
        log_lines.append("[SUCCESS] build_query_plan completed successfully")
        log_path = write_log(log_lines, as_of_date)

        print("build_query_plan completed successfully")
        print(f"dated plan: {dated_plan_path}")
        print(f"current plan: {current_plan_path}")
        print(f"log written to: {log_path}")
        return 0
    except Exception as e:
        log_lines.append(f"[ERROR] {type(e).__name__}: {e}")
        log_path = write_log(log_lines, as_of_date)
        print(f"build_query_plan failed: {e}")
        print(f"log written to: {log_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
