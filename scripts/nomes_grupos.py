"""Add product names: groups.parquet with the name of every product group that has reviews.

    python nomes_grupos.py --catalog D:\\catalogo_build\\grupos.parquet --out D:\\reviews_out   # ~1 min

--catalog takes the catalog's grupos.parquet (built) or the raw export folder (grupos/*.parquet). Reads it
and the built reviews, and writes kaggle/groups.parquet and sample/groups_sample.csv. The same names are in the
catalog dataset on Kaggle; this table saves a join with its 18 million groups.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    k, s = (args.out / "kaggle").as_posix(), (args.out / "sample").as_posix()
    con = duckdb.connect()
    source = args.catalog if args.catalog.is_file() else args.catalog / "grupos" / "*.parquet"
    con.execute(f"CREATE VIEW grupos AS SELECT * FROM read_parquet('{source.as_posix()}')")
    con.execute(f"""CREATE TABLE g AS
        SELECT r.group_id, any_value(gr.short_name) AS group_name, count(*) AS reviews,
               round(avg(r.rating), 2) AS avg_rating
        FROM read_parquet('{k}/reviews.parquet') r LEFT JOIN grupos gr ON gr.id = r.group_id
        WHERE r.group_id IS NOT NULL GROUP BY 1""")
    con.execute(f"COPY (SELECT * FROM g ORDER BY group_id) TO '{k}/groups.parquet' (FORMAT parquet, COMPRESSION zstd)")
    con.execute(f"""COPY (SELECT * FROM g WHERE group_id IN (SELECT DISTINCT group_id FROM read_csv_auto('{s}/reviews_sample.csv'))
                 ORDER BY group_id) TO '{s}/groups_sample.csv' (HEADER)""")
    n, named = con.execute("SELECT count(*), count(group_name) FROM g").fetchone()
    print(f"{n:,} groups, {named:,} with a name -> {k}/groups.parquet")


if __name__ == "__main__":
    main()
