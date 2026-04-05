import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPOOL_DIR = PROJECT_ROOT / 'spool'
DEFAULT_UNIVERSE_PATH = PROJECT_ROOT / 'data' / 'universe' / 'current' / 'kospi200.aliases.current.json'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'reports' / 'coverage'


def read_json(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_universe(universe_path: Path) -> Dict[str, dict]:
    data = read_json(universe_path)
    companies = data.get('companies', []) or []
    out: Dict[str, dict] = {}
    for c in companies:
        ticker = str(c.get('ticker', '')).strip()
        if ticker:
            out[ticker] = c
    return out


def iter_batch_files(spool_dir: Path) -> List[Path]:
    if not spool_dir.exists():
        return []
    return sorted(spool_dir.rglob('batch-*.json'))


def safe_iso_to_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def analyze(spool_dir: Path, universe_path: Path) -> dict:
    universe = load_universe(universe_path)
    batch_files = iter_batch_files(spool_dir)

    total_batch_count = len(batch_files)
    total_item_count = 0
    unique_news_ids: Set[str] = set()
    matched_company_tickers: Set[str] = set()
    companies_with_ml_articles: Set[str] = set()
    companies_with_digest_articles: Set[str] = set()

    multi_matched_item_count = 0
    unmatched_item_count = 0
    used_for_ml_true_count = 0
    used_for_digest_true_count = 0
    old_article_count = 0

    query_counter = Counter()
    query_ml_counter = Counter()
    query_digest_counter = Counter()
    source_counter = Counter()
    source_ml_counter = Counter()
    source_digest_counter = Counter()
    ml_exclusion_reason_counter = Counter()
    source_quality_counter = Counter()

    ticker_item_counter = Counter()
    ticker_unique_news_counter = Counter()
    ticker_query_counter: Dict[str, Counter] = defaultdict(Counter)
    ticker_source_counter: Dict[str, Counter] = defaultdict(Counter)
    ticker_titles: Dict[str, List[str]] = defaultdict(list)

    one_day = None

    for path in batch_files:
        batch = read_json(path)
        created_at = safe_iso_to_dt(batch.get('created_at', ''))
        if created_at and one_day is None:
            one_day = created_at

        items = batch.get('items', []) or []
        total_item_count += len(items)

        for item in items:
            news_id = str(item.get('news_id', '')).strip()
            if news_id:
                unique_news_ids.add(news_id)

            query = str(item.get('query', '')).strip()
            if query:
                query_counter[query] += 1

            source_name = str(item.get('source_name', '')).strip()
            if source_name:
                source_counter[source_name] += 1

            used_for_ml = bool(item.get('used_for_ml', False))
            used_for_digest = bool(item.get('used_for_digest', False))
            if used_for_ml:
                used_for_ml_true_count += 1
                if query:
                    query_ml_counter[query] += 1
                if source_name:
                    source_ml_counter[source_name] += 1
            if used_for_digest:
                used_for_digest_true_count += 1
                if query:
                    query_digest_counter[query] += 1
                if source_name:
                    source_digest_counter[source_name] += 1

            ml_reason = str(item.get('ml_exclusion_reason', '')).strip()
            if ml_reason:
                ml_exclusion_reason_counter[ml_reason] += 1

            source_quality = str(item.get('source_quality_tier', '')).strip()
            if source_quality:
                source_quality_counter[source_quality] += 1

            published_at = safe_iso_to_dt(item.get('published_at', ''))
            if published_at and one_day:
                delta_days = (one_day.date() - published_at.date()).days
                if delta_days > 30:
                    old_article_count += 1

            matched = item.get('matched', []) or []
            if not matched:
                unmatched_item_count += 1
                continue

            if len(matched) >= 2:
                multi_matched_item_count += 1

            for m in matched:
                ticker = str(m.get('ticker', '')).strip()
                company_name = str(m.get('company_name', '')).strip()
                if not ticker:
                    continue

                matched_company_tickers.add(ticker)
                ticker_item_counter[ticker] += 1
                if news_id:
                    ticker_unique_news_counter[ticker] += 1
                if query:
                    ticker_query_counter[ticker][query] += 1
                if source_name:
                    ticker_source_counter[ticker][source_name] += 1
                if used_for_ml:
                    companies_with_ml_articles.add(ticker)
                if used_for_digest:
                    companies_with_digest_articles.add(ticker)
                if company_name and len(ticker_titles[ticker]) < 3:
                    title = str(item.get('title', '')).strip()
                    if title:
                        ticker_titles[ticker].append(title)

    universe_size = len(universe)
    companies_with_any_hit = len(matched_company_tickers)
    zero_hit_tickers = sorted(set(universe.keys()) - matched_company_tickers)

    coverage_ratio = round(companies_with_any_hit / universe_size, 4) if universe_size else 0.0
    unique_article_count = len(unique_news_ids)
    avg_items_per_batch = round(total_item_count / total_batch_count, 2) if total_batch_count else 0.0
    avg_queries_per_company_hit = round(sum(len(c) for c in ticker_query_counter.values()) / companies_with_any_hit, 2) if companies_with_any_hit else 0.0

    per_company_rows = []
    for ticker, meta in sorted(universe.items(), key=lambda kv: kv[0]):
        company_name = str(meta.get('company_name_ko', ''))
        top_queries = ticker_query_counter[ticker].most_common(5)
        top_sources = ticker_source_counter[ticker].most_common(5)
        per_company_rows.append({
            'ticker': ticker,
            'company_name_ko': company_name,
            'matched_item_count': ticker_item_counter[ticker],
            'unique_news_count': ticker_unique_news_counter[ticker],
            'has_any_hit': ticker in matched_company_tickers,
            'has_ml_articles': ticker in companies_with_ml_articles,
            'has_digest_articles': ticker in companies_with_digest_articles,
            'top_queries': ' | '.join([f'{q}:{n}' for q, n in top_queries]),
            'top_sources': ' | '.join([f'{s}:{n}' for s, n in top_sources]),
            'sample_titles': ' || '.join(ticker_titles[ticker][:3]),
        })

    query_rows = []
    for query, count in query_counter.most_common():
        query_rows.append({
            'query': query,
            'item_count': count,
            'ml_item_count': query_ml_counter.get(query, 0),
            'digest_item_count': query_digest_counter.get(query, 0),
        })

    zero_hit_rows = []
    for ticker in zero_hit_tickers:
        meta = universe[ticker]
        zero_hit_rows.append({
            'ticker': ticker,
            'company_name_ko': str(meta.get('company_name_ko', '')),
            'market': str(meta.get('market', 'KOSPI')),
        })

    ml_blocked_source_rows = []
    for source, total in source_counter.most_common():
        ml_blocked_source_rows.append({
            'source_name': source,
            'item_count': total,
            'ml_item_count': source_ml_counter.get(source, 0),
            'digest_item_count': source_digest_counter.get(source, 0),
        })

    summary = {
        'generated_at': datetime.now().isoformat(),
        'spool_dir': str(spool_dir),
        'universe_path': str(universe_path),
        'batch_count': total_batch_count,
        'total_item_count': total_item_count,
        'unique_article_count': unique_article_count,
        'avg_items_per_batch': avg_items_per_batch,
        'universe_size': universe_size,
        'companies_with_any_hit': companies_with_any_hit,
        'companies_with_ml_articles': len(companies_with_ml_articles),
        'companies_with_digest_articles': len(companies_with_digest_articles),
        'coverage_ratio': coverage_ratio,
        'zero_hit_company_count': len(zero_hit_tickers),
        'multi_matched_item_count': multi_matched_item_count,
        'unmatched_item_count': unmatched_item_count,
        'used_for_ml_true_count': used_for_ml_true_count,
        'used_for_digest_true_count': used_for_digest_true_count,
        'old_article_count_over_30d': old_article_count,
        'avg_queries_per_hit_company': avg_queries_per_company_hit,
        'top_queries': [{'query': q, 'count': n} for q, n in query_counter.most_common(20)],
        'top_sources': [{'source_name': s, 'count': n} for s, n in source_counter.most_common(20)],
        'top_ml_exclusion_reasons': [{'reason': k, 'count': v} for k, v in ml_exclusion_reason_counter.most_common(20)],
        'top_source_quality_tiers': [{'tier': k, 'count': v} for k, v in source_quality_counter.most_common(20)],
    }

    return {
        'summary': summary,
        'per_company_rows': per_company_rows,
        'query_rows': query_rows,
        'zero_hit_rows': zero_hit_rows,
        'per_source_rows': ml_blocked_source_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Analyze spool coverage for KOSPI200 news batches')
    parser.add_argument('--spool-dir', default=str(DEFAULT_SPOOL_DIR), help='Path to spool directory')
    parser.add_argument('--universe-path', default=str(DEFAULT_UNIVERSE_PATH), help='Path to aliases current json')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'), help='Report date YYYY-MM-DD')
    args = parser.parse_args()

    spool_dir = Path(args.spool_dir)
    universe_path = Path(args.universe_path)
    report_date = args.date

    if not spool_dir.exists():
        print(f'coverage_report failed: spool dir not found: {spool_dir}')
        return 1
    if not universe_path.exists():
        print(f'coverage_report failed: universe path not found: {universe_path}')
        return 1

    report = analyze(spool_dir, universe_path)

    base_dir = DEFAULT_OUTPUT_DIR / report_date
    base_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = base_dir / f'coverage-summary-{report_date}.json'
    per_company_csv_path = base_dir / f'coverage-per-company-{report_date}.csv'
    query_csv_path = base_dir / f'coverage-per-query-{report_date}.csv'
    zero_hit_csv_path = base_dir / f'coverage-zero-hit-{report_date}.csv'
    per_source_csv_path = base_dir / f'coverage-per-source-{report_date}.csv'
    current_summary_path = DEFAULT_OUTPUT_DIR / 'current' / 'coverage-summary.current.json'

    write_json(summary_json_path, report['summary'])
    write_json(current_summary_path, report['summary'])
    write_csv(
        per_company_csv_path,
        report['per_company_rows'],
        [
            'ticker', 'company_name_ko', 'matched_item_count', 'unique_news_count',
            'has_any_hit', 'has_ml_articles', 'has_digest_articles',
            'top_queries', 'top_sources', 'sample_titles'
        ],
    )
    write_csv(
        query_csv_path,
        report['query_rows'],
        ['query', 'item_count', 'ml_item_count', 'digest_item_count'],
    )
    write_csv(
        zero_hit_csv_path,
        report['zero_hit_rows'],
        ['ticker', 'company_name_ko', 'market'],
    )
    write_csv(
        per_source_csv_path,
        report['per_source_rows'],
        ['source_name', 'item_count', 'ml_item_count', 'digest_item_count'],
    )

    print('daily_coverage_report completed successfully')
    print(f"summary json: {summary_json_path}")
    print(f"per-company csv: {per_company_csv_path}")
    print(f"per-query csv: {query_csv_path}")
    print(f"per-source csv: {per_source_csv_path}")
    print(f"zero-hit csv: {zero_hit_csv_path}")
    print(f"coverage_ratio: {report['summary']['coverage_ratio']}")
    print(f"companies_with_any_hit: {report['summary']['companies_with_any_hit']}/{report['summary']['universe_size']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
