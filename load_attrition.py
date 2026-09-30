"""
Load employee_attrition.csv (mentah, tanpa cleaning) ke PostgreSQL.
Tabel yang dibuat: ai_engineer.raw_attrition_<STUDENT_NAME>

Cara pakai (dari folder project, .env sudah terisi):
    python load_attrition.py
"""
import sys
import pandas as pd
from sqlalchemy import text

from db import engine, settings, SCHEMA, ATTRITION_TABLE_NAME

CSV_PATH = "employee_attrition.csv"


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"CSV dibaca: {df.shape[0]} baris, {df.shape[1]} kolom")
    print(f"Tujuan: {SCHEMA}.{ATTRITION_TABLE_NAME}")

    # Jangan menimpa tabel yang sudah ada (bisa saja milik orang lain).
    with engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = :t"
            ),
            {"s": SCHEMA, "t": ATTRITION_TABLE_NAME},
        ).first()
    if exists:
        print(
            f"\nBERHENTI: tabel {SCHEMA}.{ATTRITION_TABLE_NAME} sudah ada.\n"
            "Kalau itu milikmu dan mau load ulang, hapus dulu lewat DBeaver. "
            "Kalau bukan milikmu, ganti STUDENT_NAME di .env."
        )
        sys.exit(1)

    df.to_sql(
        ATTRITION_TABLE_NAME,
        engine,
        schema=SCHEMA,
        if_exists="fail",
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        n = conn.execute(
            text(f'SELECT COUNT(*) FROM "{SCHEMA}"."{ATTRITION_TABLE_NAME}"')
        ).scalar()
    print(f"\nSelesai. Jumlah baris di database: {n} (harus 1470)")


if __name__ == "__main__":
    main()
