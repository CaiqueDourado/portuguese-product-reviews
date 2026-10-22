"""Validate sample/*.csv (the CI runs it). Exits with code 1 and lists every failure.

    python scripts/validate.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "sample"
failures: list[str] = []
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


def check(ok: bool, message: str) -> None:
    if not ok:
        failures.append(message)


def main() -> int:
    columns = json.loads((ROOT / "schema" / "columns.json").read_text(encoding="utf-8"))
    tables = {}
    for name in ("reviews", "sentences", "aspect_ratings", "pros_cons", "groups"):
        path = S / f"{name}_sample.csv"
        if not path.exists():
            check(False, f"missing {path.name}")
            continue
        df = pd.read_csv(path, low_memory=False)
        tables[name] = df
        expected = [c["name"] for c in columns if c["table"] == name]
        check(list(df.columns) == expected, f"{name}: columns differ from schema/columns.json")
    r, s, a, p, g = (tables.get(n) for n in ("reviews", "sentences", "aspect_ratings", "pros_cons", "groups"))
    if r is not None:
        check(r["review_id"].is_unique, "reviews: review_id not unique")
        check(r["rating"].between(1, 5).all(), "reviews: rating outside 1-5")
        check(set(r["sentiment"].dropna()) <= {"POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"}, "reviews: unknown sentiment")
        check(not ((r["rating"] <= 2) & (r["sentiment"] == "POSITIVE")).any(), "reviews: POSITIVE with 1-2 stars left")
        check(r["helpfulness"].dropna().between(0, 1).all(), "reviews: helpfulness outside 0-1")
        text = r["text"].fillna("") + " " + r["title"].fillna("")
        check(not text.str.contains(EMAIL).any(), "reviews: e-mail left in a text")
        check(not text.str.contains(CPF).any(), "reviews: CPF left in a text")
        restored = r["tilde_restored"].astype(str).str.lower() == "true"
        check((r.loc[restored, "text_original"].notna()).all(), "reviews: restored text without text_original")
        check(r.loc[~restored, "text_original"].isna().all(), "reviews: text_original on a row not restored")
        check(pd.to_datetime(r["submitted_at"], errors="coerce").notna().all(), "reviews: bad submitted_at")
        check(r["group_id"].nunique() <= 2000, "reviews: sample has more than 2,000 groups")
    if s is not None and r is not None:
        check(s["sentence_id"].is_unique, "sentences: sentence_id not unique")
        check(s["review_id"].isin(r["review_id"]).all(), "sentences: review not in the sample")
        check((s["text"].str.len() <= 300).all(), "sentences: clause over 300 characters")
    if a is not None:
        check(a["score"].between(1, 5).all(), "aspect_ratings: score outside 1-5")
        check(a["aspect"].notna().all(), "aspect_ratings: aspect without a name")
    if p is not None:
        check(set(p["kind"]) <= {"pro", "con"}, "pros_cons: kind must be pro or con")
        check(p["rank"].between(1, 4).all(), "pros_cons: rank outside 1-4")
        check(p["clause"].str.contains(" ").all(), "pros_cons: one-word clause")
        check(not p.duplicated(["group_id", "kind", "rank"]).any(), "pros_cons: duplicated rank")
    if g is not None and r is not None:
        check(g["group_id"].is_unique, "groups: group_id not unique")
        check(g["group_id"].isin(r["group_id"]).all(), "groups: group without reviews in the sample")
    if failures:
        print(f"{len(failures)} check(s) failed:")
        for m in failures:
            print(" -", m)
        return 1
    print("OK:", ", ".join(f"{k} {len(v):,}" for k, v in tables.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
