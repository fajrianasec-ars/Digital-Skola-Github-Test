"""
Pipeline

Dua path ke cloud PostgreSQL:
  Path A — ETL:  scrape → clean di pandas → load CLEAN
  Path B — ELT:  read CSV → load RAW → transform di SQL

Cara menjalankan:
    python pipeline.py --attrition-csv "path/to/employee_attrition.csv"
"""

import argparse
import logging

import pandas as pd
from sqlalchemy import text

from db import engine, init_db, save_articles, count_articles, ARTICLES_TABLE, ATTRITION_TABLE_NAME, SCHEMA
from scraper import scrape_all
from cleaner import clean_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


def run_etl_scraping(rss: bool, book_pages: int, quote_pages: int) -> None:
    print("\n" + "=" * 60)
    print("  PATH A: ETL — Scrape → Clean → Load")
    print("=" * 60)

    print("\n[Extract] Scraping data dari web...")
    raw = scrape_all(rss=rss, book_pages=book_pages, quote_pages=quote_pages)
    print(f"  → Scraped: {len(raw)} raw records")

    print("\n[Transform] Cleaning data dengan Pandas...")
    df = clean_articles(raw)
    print(f"  → Cleaned: {len(df)} records")
    print(f"  → Sources: {df['source'].value_counts().to_dict()}")

    print(f"\n[Load] Menyimpan ke tabel {ARTICLES_TABLE}...")
    inserted = save_articles(df)
    total = count_articles()
    print(f"  → Inserted: {inserted} baru (duplikat di-skip)")
    print(f"  → Total di database: {total}")


def run_elt_attrition(csv_path: str) -> None:
    print("\n" + "=" * 60)
    print("  PATH B: ELT — Load Raw → Transform in SQL")
    print("=" * 60)

    print(f"\n[Extract + Load] Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"  → {len(df)} rows, {len(df.columns)} columns")
    print(f"  → Columns: {list(df.columns[:8])}...")
    print(f"  → Nulls: {df.isnull().sum().sum()} total")
    print(f"  → Loading RAW, TANPA cleaning...")

    df.to_sql(
        ATTRITION_TABLE_NAME,
        engine,
        if_exists="replace",
        index=False,
        schema=SCHEMA,
    )

    print(f"  → Loaded table: {SCHEMA}.{ATTRITION_TABLE_NAME} (data mentah)")


def run_sql_transforms(sql_path: str) -> None:
    from db import ATTRITION_TABLE_NAME

    with open(sql_path, encoding="utf-8") as f:
        sql_script = f.read()

    sql_script = sql_script.replace("raw_attrition", ATTRITION_TABLE_NAME)

    with engine.connect() as conn:
        for statement in sql_script.split(";"):
            clean = statement.strip()
            if not clean or all(
                line.strip().startswith("--") or not line.strip()
                for line in clean.split("\n")
            ):
                continue

            print(f"\n  SQL: {clean[:70]}...")
            result = conn.execute(text(clean))
            if result.returns_rows:
                rows = result.fetchall()
                for row in rows[:5]:
                    print(f"    {row}")
                if len(rows) > 5:
                    print(f"    ... ({len(rows)} rows total)")
            print("  ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Session 9 — ETL vs ELT Demo")
    parser.add_argument(
        "--attrition-csv", required=True,
        help="Path to IBM HR Attrition CSV (download from Kaggle)",
    )
    parser.add_argument(
        "--book-pages", type=int, default=10,
        help="Book catalogue pages to scrape (default: 10)",
    )
    parser.add_argument(
        "--quote-pages", type=int, default=10,
        help="Quote pages to scrape (default: 10)",
    )
    parser.add_argument(
        "--no-rss", action="store_true",
        help="Skip RSS feeds (faster demo if internet is slow)",
    )
    parser.add_argument(
        "--skip-scraping", action="store_true",
        help="Skip all scraping, only run the CSV/ELT path",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  SESSION 9 — SQL, Scraping & Data Cleaning Pipeline")
    print("=" * 60)

    print("\nStep 0: Inisialisasi Database...")
    init_db()

    if not args.skip_scraping:
        run_etl_scraping(
            rss=not args.no_rss,
            book_pages=args.book_pages,
            quote_pages=args.quote_pages,
        )

    # Attrition is already loaded separately by load_attrition.py.
    # Do not overwrite the existing raw attrition table when running this pipeline.
    if not args.skip_scraping:
        print("\nPath B dilewati: data attrition sudah di-load oleh load_attrition.py.")

    print("\n" + "=" * 60)
    print("  PIPELINE SELESAI")
    print("=" * 60 + "\n")
