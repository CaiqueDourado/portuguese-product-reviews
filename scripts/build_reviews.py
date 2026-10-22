"""Build the reviews dataset from the raw export (runs locally: Python + pyarrow + DuckDB).

    python -m pip install --user duckdb pyarrow
    python build_reviews.py --raw D:\\reviews_raw --out D:\\reviews_out        # ~15-30 min

Writes to --out:
    kaggle/reviews.parquet              2.87 M reviews, typed, cleaned
    kaggle/sentences.parquet            12.9 M clauses from the 2020 Stanford POS split
    kaggle/aspect_ratings.parquet       2.5 M secondary ratings (quality, design, battery...)
    kaggle/pros_cons.parquet            top 4 pros and 4 cons per product group (the 2020 method)
    sample/*.csv                        every row of 2,000 random product groups (for GitHub)
    stats.json                          counts of every step (send this and sample/ back)

Rules (docs/methodology.md):
  * no personal columns exist in the export; e-mails, phone numbers and CPFs inside the text are masked;
  * dates are parsed from their two formats (dd/MM/yyyy HH:mm:ss and M/d/yyyy h:mm:ss AM);
  * ~27% of the texts lost every ã/õ during collection ("nao", "opçao") while keeping the other accents;
    those words are restored from the spelling the same word has in the intact texts, and the original
    text is kept in text_original;
  * constant or empty columns (Pros, Cons, RatingRange, ModerationStatus, tipoVerificacao) are dropped.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b")
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
WORD = re.compile(r"[A-Za-zÀ-ÿ]+")
TILDE = re.compile(r"[ãõÃÕ]")
OTHER_ACCENT = re.compile(r"[áéíóúâêôàçÁÉÍÓÚÂÊÔÀÇ]")
STRIP_TILDE = str.maketrans("ãõÃÕ", "aoAO")
STORES = {"LeroyMerlin": "Leroy Merlin", "FastShop": "Fast Shop"}


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def to_int(value: str | None) -> int | None:
    f = to_float(value)
    return None if f is None else int(f)


def to_bool(value: str | None) -> bool | None:
    return {"True": True, "False": False}.get((value or "").strip())


def mask(text: str | None, counts: Counter) -> str | None:
    if not text:
        return text
    for name, pattern, label in (("email", EMAIL, "[e-mail]"), ("cpf", CPF, "[cpf]"), ("phone", PHONE, "[telefone]")):
        text, n = pattern.subn(label, text)
        counts[name] += n
    return text


def lost_tilde(text: str | None) -> bool:
    """ã/õ dropped by the collector: no ã/õ at all, but other accents are there (the writer used accents)."""
    return bool(text) and not TILDE.search(text) and bool(OTHER_ACCENT.search(text))


def build_tilde_map(raw: Path) -> dict[str, str]:
    """stripped word -> accented spelling, learnt from the texts that kept their ã/õ."""
    accented, plain = Counter(), Counter()
    for batch in ds.dataset(raw / "reviews").to_batches(columns=["ReviewText"], batch_size=200_000):
        for text in batch.column(0).to_pylist():
            if not text or not TILDE.search(text):
                continue
            for word in WORD.findall(text.lower()):
                if TILDE.search(word):
                    accented[word] += 1
                else:
                    plain[word] += 1
    best: dict[str, tuple[str, int]] = {}
    for word, n in accented.items():
        key = word.translate(STRIP_TILDE)
        if n >= 5 and n >= 5 * plain.get(key, 0) and (key not in best or n > best[key][1]):
            best[key] = (word, n)
    return {k: v[0] for k, v in best.items()}


def restore(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    changed = 0

    def fix(m: re.Match) -> str:
        nonlocal changed
        word = m.group(0)
        hit = mapping.get(word.lower())
        if not hit:
            return word
        changed += 1
        if word.isupper():
            return hit.upper()
        if word[0].isupper():
            return hit[0].upper() + hit[1:]
        return hit

    return WORD.sub(fix, text), changed


REVIEW_SCHEMA = pa.schema([
    ("review_id", pa.int64()), ("product_id", pa.int64()), ("group_id", pa.int64()), ("store", pa.string()),
    ("rating", pa.int8()), ("recommended", pa.bool_()), ("ratings_only", pa.bool_()),
    ("title", pa.string()), ("text", pa.string()), ("text_original", pa.string()), ("tilde_restored", pa.bool_()),
    ("sentiment", pa.string()), ("sentiment_aws_original", pa.string()),
    ("helpfulness", pa.float32()), ("feedback_positive", pa.int32()), ("feedback_negative", pa.int32()),
    ("comments", pa.int32()), ("submitted_at", pa.timestamp("s")), ("modified_at", pa.timestamp("s")),
    ("locale", pa.string()), ("syndicated", pa.bool_()), ("campaign", pa.string()), ("collected_at", pa.timestamp("ms")),
])


def build_reviews(raw: Path, out: Path, stats: dict) -> None:
    mapping = build_tilde_map(raw)
    stats["tilde_map_words"] = len(mapping)
    counts = Counter()
    writer = pq.ParquetWriter(out / "kaggle" / "reviews.parquet", REVIEW_SCHEMA, compression="zstd")
    for batch in ds.dataset(raw / "reviews").to_batches(batch_size=200_000):
        rows = batch.to_pylist()
        cols = {f.name: [] for f in REVIEW_SCHEMA}
        for r in rows:
            text = mask(r["ReviewText"], counts)
            title = mask(r["Title"], counts) or None
            original, restored = None, False
            if text and lost_tilde(text):
                fixed, n = restore(text, mapping)
                if n:
                    original, text, restored = text, fixed, True
                    counts["tilde_words"] += n
            counts["tilde_restored"] += restored
            values = {
                "review_id": r["id"], "product_id": r["idCrawlerNewProductDetail"], "group_id": r["productGroupId"],
                "store": STORES.get(r["varejistaOrigem"], r["varejistaOrigem"]), "rating": to_int(r["Rating"]),
                "recommended": to_bool(r["IsRecommended"]), "ratings_only": to_bool(r["IsRatingsOnly"]),
                "title": title, "text": text or None, "text_original": original, "tilde_restored": restored,
                "sentiment": r["sentiment"] or None, "sentiment_aws_original": r["sentiment_original_aws_translate"] or None,
                "helpfulness": to_float(r["Helpfulness"]), "feedback_positive": to_int(r["TotalPositiveFeedbackCount"]),
                "feedback_negative": to_int(r["TotalNegativeFeedbackCount"]), "comments": to_int(r["TotalCommentCount"]),
                "submitted_at": parse_time(r["SubmissionTime"]), "modified_at": parse_time(r["LastModificationTime"]),
                "locale": r["ContentLocale"] or None, "syndicated": to_bool(r["IsSyndicated"]),
                "campaign": r["CampaignId"] or None, "collected_at": r["dataGravacao"],
            }
            counts["bad_date"] += bool(r["SubmissionTime"]) and values["submitted_at"] is None
            for k, v in values.items():
                cols[k].append(v)
        writer.write_table(pa.table(cols, schema=REVIEW_SCHEMA))
        counts["reviews"] += len(rows)
        print(f"reviews: {counts['reviews']:,}", flush=True)
    writer.close()
    stats["reviews"] = dict(counts)


def build_rest(raw: Path, out: Path, stats: dict, sample_groups: int) -> None:
    con = duckdb.connect()
    k, s = (out / "kaggle").as_posix(), (out / "sample").as_posix()
    con.execute(f"CREATE VIEW raw_sent AS SELECT * FROM read_parquet('{(raw / 'sentencas').as_posix()}/*.parquet')")
    con.execute(f"CREATE VIEW raw_notes AS SELECT * FROM read_parquet('{(raw / 'notas_caracteristicas').as_posix()}/*.parquet')")
    con.execute(f"CREATE VIEW titles AS SELECT * FROM read_parquet('{(raw / 'caracteristicas_titulos').as_posix()}/*.parquet')")
    con.execute(f"CREATE VIEW reviews AS SELECT * FROM read_parquet('{k}/reviews.parquet')")
    con.execute(f"""COPY (
        SELECT s.id AS sentence_id, s.idCrawlerNewProductReview AS review_id, s.productGroupId AS group_id,
               s.text, s.annotatedText AS tagged, s.normalizada AS canonical, s.quantidade AS count_site,
               s.metaphone AS key_metaphone, s.fingerprint AS key_fingerprint, s.tokenizada AS key_tokens,
               s.tokenizada_fingerprint AS key_tokens_fingerprint, s.ngram AS key_ngram, s.soft AS key_soft
        FROM raw_sent s ORDER BY s.id) TO '{k}/sentences.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"""COPY (
        SELECT n.idCrawlerNewProductReview AS review_id, n.chave AS aspect_key, coalesce(t.titulo, n.chave) AS aspect,
               CAST(n.valor AS TINYINT) AS score
        FROM raw_notes n LEFT JOIN titles t USING (chave) ORDER BY n.id) TO '{k}/aspect_ratings.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    # The 2020 method (procedure "Tabela 15"): per group and sentiment, the 4 canonical clauses with a
    # space that appear most, ties broken by how often the clause appears across the whole site.
    con.execute(f"""COPY (
        WITH c AS (
            SELECT r.group_id, r.sentiment, s.normalizada AS clause, count(*) AS mentions, max(s.quantidade) AS count_site,
                   min(r.review_id) AS example_review_id
            FROM raw_sent s JOIN reviews r ON r.review_id = s.idCrawlerNewProductReview
            WHERE r.sentiment IN ('POSITIVE', 'NEGATIVE') AND s.normalizada LIKE '% %' AND r.group_id IS NOT NULL
            GROUP BY ALL)
        SELECT group_id, CASE sentiment WHEN 'POSITIVE' THEN 'pro' ELSE 'con' END AS kind,
               row_number() OVER (PARTITION BY group_id, sentiment ORDER BY mentions DESC, count_site DESC, clause) AS rank,
               clause, mentions, count_site, example_review_id
        FROM c QUALIFY rank <= 4 ORDER BY group_id, kind DESC, rank) TO '{k}/pros_cons.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"""CREATE TABLE groups_sample AS SELECT group_id FROM (SELECT DISTINCT group_id FROM reviews WHERE group_id IS NOT NULL)
                    USING SAMPLE {sample_groups} ROWS (reservoir, 42)""")
    for name, query in {
        "reviews": f"SELECT * FROM reviews WHERE group_id IN (SELECT group_id FROM groups_sample) ORDER BY review_id",
        "sentences": f"SELECT * FROM read_parquet('{k}/sentences.parquet') WHERE group_id IN (SELECT group_id FROM groups_sample) ORDER BY sentence_id",
        "aspect_ratings": f"SELECT a.* FROM read_parquet('{k}/aspect_ratings.parquet') a JOIN reviews r USING (review_id) WHERE r.group_id IN (SELECT group_id FROM groups_sample)",
        "pros_cons": f"SELECT * FROM read_parquet('{k}/pros_cons.parquet') WHERE group_id IN (SELECT group_id FROM groups_sample)",
    }.items():
        con.execute(f"COPY ({query}) TO '{s}/{name}_sample.csv' (HEADER)")
    for table in ("sentences", "aspect_ratings", "pros_cons"):
        stats[table] = con.execute(f"SELECT count(*) FROM read_parquet('{k}/{table}.parquet')").fetchone()[0]
    stats["by_store"] = dict(con.execute("SELECT store, count(*) FROM reviews GROUP BY 1 ORDER BY 2 DESC").fetchall())
    stats["by_rating"] = {str(a): b for a, b in con.execute("SELECT rating, count(*) FROM reviews GROUP BY 1 ORDER BY 1").fetchall()}
    stats["sentiment_by_rating"] = [list(r) for r in con.execute(
        "SELECT rating, sentiment, count(*) FROM reviews GROUP BY 1, 2 ORDER BY 1, 2").fetchall()]
    stats["submitted"] = [str(x) for x in con.execute("SELECT min(submitted_at), max(submitted_at) FROM reviews").fetchone()]
    stats["by_year"] = {str(a): b for a, b in con.execute(
        "SELECT year(submitted_at), count(*) FROM reviews GROUP BY 1 ORDER BY 1").fetchall()}
    stats["groups"] = con.execute("SELECT count(DISTINCT group_id) FROM reviews").fetchone()[0]
    stats["products"] = con.execute("SELECT count(DISTINCT product_id) FROM reviews").fetchone()[0]
    stats["groups_with_pros_cons"] = con.execute(f"SELECT count(DISTINCT group_id) FROM read_parquet('{k}/pros_cons.parquet')").fetchone()[0]
    stats["duckdb"] = duckdb.__version__


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--sample-groups", type=int, default=2000)
    args = ap.parse_args()
    (args.out / "kaggle").mkdir(parents=True, exist_ok=True)
    (args.out / "sample").mkdir(parents=True, exist_ok=True)
    stats: dict = {}
    build_reviews(args.raw, args.out, stats)
    build_rest(args.raw, args.out, stats, args.sample_groups)
    (args.out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
