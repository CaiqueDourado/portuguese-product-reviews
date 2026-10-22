"""Export the product reviews (base 11) from the author's SQL Server into Parquet files (raw layer).

Same exporter as the catalog: keyset pagination by id, one Parquet file per block, resumable.

    python -m pip install --user pyodbc pyarrow
    python exportar_reviews.py --out D:\\reviews_raw              # every table (~5 GB free)
    python exportar_reviews.py --out D:\\reviews_raw --status     # progress only

Personal data never leaves the database: UserNickname, UserLocation, AuthorId, SubmissionId, IdReview
and the key built from them are not selected. Windows authentication, no password in the script.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

DL = "nlp_data_lake.dbo"


@dataclass
class Table:
    name: str
    source: str              # schema-qualified table
    columns: list[tuple[str, str, pa.DataType]]  # (SQL expression, output name, Arrow type)
    block: int = 500_000
    small: bool = False      # no id column: exported whole, in one file

    @property
    def select(self) -> str:
        return ", ".join(f"{expr} AS [{name}]" for expr, name, _ in self.columns)

    @property
    def schema(self) -> pa.Schema:
        return pa.schema([(name, kind) for _, name, kind in self.columns])


S, I, B, F, T = pa.string(), pa.int64(), pa.bool_(), pa.float64(), pa.timestamp("ms")


TABLES = [
    Table("reviews", f"{DL}.CrawlerNewProductReview", [
        ("id", "id", I), ("idCrawlerNewProduct", "idCrawlerNewProduct", I),
        ("idCrawlerNewProductDetail", "idCrawlerNewProductDetail", I), ("productGroupId", "productGroupId", I),
        ("varejistaOrigem", "varejistaOrigem", S), ("Rating", "Rating", S), ("RatingRange", "RatingRange", S),
        ("IsRecommended", "IsRecommended", S), ("IsRatingsOnly", "IsRatingsOnly", S), ("Title", "Title", S),
        ("ReviewText", "ReviewText", S), ("Pros", "Pros", S), ("Cons", "Cons", S),
        ("Helpfulness", "Helpfulness", S), ("TotalFeedbackCount", "TotalFeedbackCount", S),
        ("TotalPositiveFeedbackCount", "TotalPositiveFeedbackCount", S),
        ("TotalNegativeFeedbackCount", "TotalNegativeFeedbackCount", S), ("TotalCommentCount", "TotalCommentCount", S),
        ("SubmissionTime", "SubmissionTime", S), ("LastModificationTime", "LastModificationTime", S),
        ("LastModeratedTime", "LastModeratedTime", S), ("ModerationStatus", "ModerationStatus", S),
        ("ContentLocale", "ContentLocale", S), ("IsFeatured", "IsFeatured", S), ("IsSyndicated", "IsSyndicated", S),
        ("CampaignId", "CampaignId", S), ("tipoVerificacao", "tipoVerificacao", S), ("chave_valor", "chave_valor", S),
        ("sentiment", "sentiment", S), ("sentiment_original_aws_translate", "sentiment_original_aws_translate", S),
        ("dataGravacao", "dataGravacao", T), ("idTopico", "idTopico", I),
    ]),
    Table("sentencas", f"{DL}.CrawlerNewProductReviewSentence_StanfordTagger", [
        ("id", "id", I), ("idCrawlerNewProductReview", "idCrawlerNewProductReview", I),
        ("productGroupId", "productGroupId", I), ("text", "text", S), ("annotatedText", "annotatedText", S),
        ("metaphone", "metaphone", S), ("ngram", "ngram", S), ("fingerprint", "fingerprint", S),
        ("tokenizada", "tokenizada", S), ("tokenizada_fingerprint", "tokenizada_fingerprint", S),
        ("soft", "soft", S), ("normalizada", "normalizada", S),
        ("normalizada_geral_todo_db", "normalizada_geral_todo_db", S), ("quantidade", "quantidade", I),
    ], block=2_000_000),
    Table("notas_caracteristicas", f"{DL}.CrawlerNewProductReviewChaveValor", [
        ("id", "id", I), ("idCrawlerNewProductReview", "idCrawlerNewProductReview", I),
        ("chave", "chave", S), ("valor", "valor", I),
    ], block=2_000_000),
    Table("caracteristicas_titulos", f"{DL}.CrawlerNewProductReviewChaveValorTitulo", [
        ("chave", "chave", S), ("titulo", "titulo", S),
    ], small=True),
]
BY_NAME = {t.name: t for t in TABLES}


BROKEN_TEXT = {"values": 0}


def decode_utf16(raw: bytes | None) -> str | None:
    """nvarchar comes as UTF-16. Some scraped texts hold half of an emoji (a lone surrogate), which
    is invalid UTF-16 and makes pyodbc fail; those characters become U+FFFD and are counted."""
    if raw is None:
        return None
    try:
        return raw.decode("utf-16-le")
    except UnicodeDecodeError:
        BROKEN_TEXT["values"] += 1
        return raw.decode("utf-16-le", errors="replace")


def connect(server: str):
    import pyodbc

    connection = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};Trusted_Connection=yes",
        autocommit=True,
    )
    for sql_type in (pyodbc.SQL_WVARCHAR, pyodbc.SQL_WCHAR, pyodbc.SQL_WLONGVARCHAR):
        connection.add_output_converter(sql_type, decode_utf16)
    return connection


def last_id(folder: Path) -> int:
    """Highest id already exported, read from the file names (part-<first>-<last>.parquet)."""
    ends = [int(p.stem.rsplit("-", 1)[1]) for p in folder.glob("part-*.parquet") if p.stem != "part-all"]
    return max(ends, default=0)


def estimated_rows(cursor, table: Table) -> int:
    """Row count from catalog metadata: instant, unlike COUNT(*) on hundreds of millions of rows."""
    db, schema, name = table.source.split(".")
    cursor.execute(
        f"SELECT SUM(p.rows) FROM {db}.sys.partitions p JOIN {db}.sys.objects o ON o.object_id = p.object_id "
        f"WHERE o.name = ? AND p.index_id IN (0, 1)", name)
    return int(cursor.fetchone()[0] or 0)


def to_arrow(rows: list, table: Table) -> pa.Table:
    columns = list(zip(*rows)) if rows else [[] for _ in table.columns]
    arrays = [pa.array(list(values), type=kind) for values, (_, _, kind) in zip(columns, table.columns)]
    return pa.Table.from_arrays(arrays, schema=table.schema)


def export(cursor, table: Table, out: Path) -> None:
    folder = out / table.name
    folder.mkdir(parents=True, exist_ok=True)
    if table.small:
        cursor.execute(f"SELECT {table.select} FROM {table.source} WITH (NOLOCK)")
        rows = cursor.fetchall()
        pq.write_table(to_arrow(rows, table), folder / "part-all.parquet", compression="zstd")
        print(f"== {table.name}: {len(rows):,} rows")
        return
    start = last_id(folder)
    total = estimated_rows(cursor, table)
    done = sum(pq.ParquetFile(p).metadata.num_rows for p in folder.glob("part-*.parquet"))
    print(f"== {table.name}: about {total:,} rows, {done:,} already exported, resuming after id {start:,}")
    query = (f"SELECT TOP ({table.block}) {table.select} FROM {table.source} WITH (NOLOCK) "
             f"WHERE id > ? ORDER BY id")
    began = time.time()
    exported = 0
    while True:
        cursor.execute(query, start)
        rows = cursor.fetchall()
        if not rows:
            break
        first, last = rows[0][0], rows[-1][0]
        target = folder / f"part-{first:012d}-{last:012d}.parquet"
        temporary = target.with_suffix(".tmp")
        pq.write_table(to_arrow(rows, table), temporary, compression="zstd")
        temporary.replace(target)  # a block is either fully written or absent
        start = last
        exported += len(rows)
        done += len(rows)
        rate = exported / max(time.time() - began, 1)
        left = max(total - done, 0) / rate if rate else 0
        print(f"   {done:,}/{total:,} rows  ({rate:,.0f}/s, about {left / 60:,.0f} min left)", flush=True)
        if len(rows) < table.block:
            break
    print(f"   {table.name} finished: {done:,} rows in {folder}")
    if BROKEN_TEXT["values"]:
        print(f"   {BROKEN_TEXT['values']:,} text values had broken characters (half emojis), replaced by U+FFFD")
        BROKEN_TEXT["values"] = 0


def status(out: Path) -> None:
    for table in TABLES:
        files = list((out / table.name).glob("part-*.parquet"))
        rows = sum(pq.ParquetFile(p).metadata.num_rows for p in files)
        size = sum(p.stat().st_size for p in files) / 1e9
        print(f"{table.name:16} {len(files):5} files {rows:15,} rows {size:8.2f} GB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="folder for the Parquet files (needs ~5 GB free)")
    parser.add_argument("--tables", nargs="*", default=[t.name for t in TABLES], choices=list(BY_NAME))
    parser.add_argument("--server", default="localhost")
    parser.add_argument("--status", action="store_true", help="show what was exported and stop")
    args = parser.parse_args()
    if args.status:
        status(args.out)
        return
    cursor = connect(args.server).cursor()
    try:
        for name in args.tables:
            export(cursor, BY_NAME[name], args.out)
    except KeyboardInterrupt:
        print("\nStopped. Run the same command again to resume.", file=sys.stderr)


if __name__ == "__main__":
    main()
