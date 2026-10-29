"""Write one product with its reviews as nested JSON (docs/example-product.json), built from the sample.

    python scripts/make_json.py

Joins sample/*_sample.csv: product group -> its reviews -> each review's aspect scores and clauses ->
the product's pros and cons. The group is fixed (GROUP_ID): an electric coffee maker with 20 reviews,
1 to 5 stars, and 4 pros and 4 cons. Needs pandas (requirements.txt).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample"
GROUP_ID = 2679579


def clean(v):
    """NaN -> None, numpy scalars -> plain Python."""
    if v is None or v is pd.NA or (isinstance(v, float) and math.isnan(v)):
        return None
    return v.item() if hasattr(v, "item") else v


def read(name: str) -> pd.DataFrame:
    frame = pd.read_csv(SAMPLE / f"{name}_sample.csv")
    return frame.loc[frame["group_id"] == GROUP_ID] if "group_id" in frame else frame


def build() -> dict:
    group = read("groups").iloc[0]
    reviews = read("reviews").sort_values("review_id")
    sentences = read("sentences").sort_values("sentence_id")
    aspects = read("aspect_ratings")
    pros_cons = read("pros_cons").sort_values("rank")

    out_reviews = []
    for _, r in reviews.iterrows():
        rid = r["review_id"]
        out_reviews.append({
            "review_id": int(rid),
            "product_id": int(r["product_id"]),
            "store": r["store"],
            "rating": int(r["rating"]),
            "recommended": clean(r["recommended"]),
            "title": clean(r["title"]),
            "text": clean(r["text"]),
            "sentiment": clean(r["sentiment"]),
            "helpfulness": clean(r["helpfulness"]),
            "submitted_at": clean(r["submitted_at"]),
            "aspects": {a["aspect"]: int(a["score"]) for _, a in aspects.loc[aspects["review_id"] == rid].iterrows()},
            "clauses": [{"text": s["text"], "canonical": s["canonical"], "count_site": int(s["count_site"])}
                        for _, s in sentences.loc[sentences["review_id"] == rid].iterrows()],
        })

    def pc(kind: str) -> list[dict]:
        rows = pros_cons.loc[pros_cons["kind"] == kind]
        return [{"clause": p["clause"], "mentions": int(p["mentions"]), "count_site": int(p["count_site"]),
                 "example_review_id": int(p["example_review_id"])} for _, p in rows.iterrows()]

    return {
        "group": {"group_id": int(group["group_id"]), "group_name": group["group_name"],
                  "reviews": int(group["reviews"]), "avg_rating": float(group["avg_rating"])},
        "reviews": out_reviews,
        "pros": pc("pro"),
        "cons": pc("con"),
    }


def main() -> None:
    rec = build()
    out = ROOT / "docs" / "example-product.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out, len(rec["reviews"]), "reviews")


if __name__ == "__main__":
    main()
