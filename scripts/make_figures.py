"""Figure for README and Kaggle (EN and PT): sentiment by stars. Reads stats.json. Cover: make_cover.py.

    python scripts/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
FONT = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
INK, MUTED, LINE, BG = "#111111", "#555555", "#e6e6e6", "#fdfdfc"
COLORS = {"POSITIVE": "#2a78d6", "MIXED": "#9aa5b1", "NEUTRAL": "#d9d9d9", "NEGATIVE": "#d6452a"}
for family in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(family, fallback_to_default=False)
        plt.rcParams["font.family"] = family
        break
    except ValueError:
        continue
TEXT = {
    "en": {"suffix": "", "title": "What AWS Comprehend said, by the stars the customer gave",
           "sub": "{n} reviews · share of each sentiment label per rating", "stars": "{s} star{p}",
           "cover_title": "Product reviews with pros and cons", "cover_sub": "{n} reviews · 9 Brazilian stores · {s} clauses · pros and cons of {g} products",
           "review": "One review", "clauses": "Clauses (punctuation and conjunctions)", "cons": "Top cons of the product", "sentiment": "Sentiment: NEGATIVE",
           "note": "Example built from the reviews of a\nbedside table in the author's slides",
           "sub2": "1-2 star reviews labelled POSITIVE were changed to NEGATIVE in 2020"},
    "pt": {"suffix": ".pt-BR", "title": "O que o AWS Comprehend disse, pelas estrelas que o cliente deu",
           "sub": "{n} reviews · proporção de cada sentimento por nota", "stars": "{s} estrela{p}",
           "cover_title": "Reviews de produtos com prós e contras", "cover_sub": "{n} reviews · 9 lojas brasileiras · {s} cláusulas · prós e contras de {g} produtos",
           "review": "Um review", "clauses": "Cláusulas (pontuação e conjunções)", "cons": "Principais contras do produto", "sentiment": "Sentimento: NEGATIVE",
           "note": "Exemplo montado com os reviews de um\ncriado-mudo da apresentação do autor",
           "sub2": "Reviews de 1-2 estrelas rotulados POSITIVE viraram NEGATIVE em 2020"},
}
REVIEW = "Não Recomendo, vão entre as gavetas e entre a gaveta e a estrutura. A parte inferior da gaveta não dá encaixe e com isso fica impossível fechar a parte traseira do mesmo. Produto de BAIXA QUALIDADE!"
CLAUSES = ["Não Recomendo", "vão entre as gavetas", "Entre a gaveta", "A estrutura", "A parte inferior da gaveta não dá encaixe",
           "Com isso fica impossível fechar a parte traseira do mesmo", "Produto de BAIXA QUALIDADE"]
CONS = ["Produto de baixa qualidade", "Peças frágeis", "Material fraco", "Dificílimo de montar"]


def fmt(n: int, lang: str) -> str:
    return f"{n:,}".replace(",", "." if lang == "pt" else ",")


def chart(stats: dict, lang: str, t: dict) -> None:
    rows = {}
    for rating, label, n in stats["sentiment_by_rating"]:
        if label:
            rows.setdefault(rating, {})[label] = n
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=110)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.78, bottom=0.1)
    fig.text(0.02, 0.92, t["title"], fontsize=15, weight="bold", color=INK)
    fig.text(0.02, 0.86, t["sub"].format(n=fmt(stats["reviews"]["reviews"], lang)) + " · " + t["sub2"], fontsize=10, color=MUTED)
    for y, rating in enumerate(sorted(rows, reverse=True)):
        total, left = sum(rows[rating].values()), 0
        for label in ("POSITIVE", "MIXED", "NEUTRAL", "NEGATIVE"):
            share = rows[rating].get(label, 0) / total
            ax.barh(y, share, left=left, color=COLORS[label], label=label if y == 0 else None, height=0.62)
            if share > 0.06:
                ax.text(left + share / 2, y, f"{share:.0%}", ha="center", va="center", fontsize=9,
                        color="white" if label in ("POSITIVE", "NEGATIVE") else INK)
            left += share
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([t["stars"].format(s=r, p="" if r == 1 else "s") for r in sorted(rows, reverse=True)], fontsize=10)
    ax.set_xticks([])
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    ax.legend(ncol=4, frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0, 1.1))
    fig.savefig(OUT / f"sentiment-by-rating{t['suffix']}.png", facecolor="white")
    plt.close(fig)


def wrap(d, text, font, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if d.textlength(test, font=font) > width:
            lines.append(line)
            line = w
        else:
            line = test
    return lines + [line]


def cover(stats: dict, lang: str, t: dict) -> None:
    f = lambda w, s: ImageFont.truetype(FONT.format(w), s)  # noqa: E731
    im = Image.new("RGB", (1120, 560), BG)
    d = ImageDraw.Draw(im)
    d.text((48, 40), t["cover_title"], font=f("Bold", 38), fill=INK)
    d.text((48, 94), t["cover_sub"].format(n=fmt(stats["reviews"]["reviews"], lang), s=fmt(stats["sentences"], lang),
                                           g=fmt(stats["groups_with_pros_cons"], lang)), font=f("Regular", 17), fill=MUTED)
    d.line((48, 132, 1072, 132), fill=LINE)
    # column 1: review
    d.text((48, 150), t["review"], font=f("SemiBold", 15), fill=MUTED)
    d.text((48, 175), t["sentiment"], font=f("SemiBold", 13), fill=COLORS["NEGATIVE"])
    y = 200
    for line in wrap(d, REVIEW, f("Regular", 15), 290):
        d.text((48, y), line, font=f("Regular", 15), fill=INK)
        y += 22
    # column 2: clauses
    d.text((380, 150), t["clauses"], font=f("SemiBold", 15), fill=MUTED)
    y = 178
    for c in CLAUSES:
        lines = wrap(d, c, f("Regular", 14), 330)
        h = 10 + 19 * len(lines)
        d.rounded_rectangle((380, y, 720, y + h), radius=6, outline="#cfd8e3", fill="#ffffff")
        for i, line in enumerate(lines):
            d.text((390, y + 5 + 19 * i), line, font=f("Regular", 14), fill=INK)
        y += h + 7
    # column 3: cons
    d.text((760, 150), t["cons"], font=f("SemiBold", 15), fill=MUTED)
    y = 182
    for i, c in enumerate(CONS, 1):
        d.rounded_rectangle((760, y, 1072, y + 40), radius=8, fill="#fbebeb")
        d.text((774, y + 10), f"{i}  {c}", font=f("Regular", 16), fill=INK)
        y += 50
    for x in (352, 736):
        d.text((x, 300), "→", font=f("Bold", 26), fill=MUTED)
    d.text((760, 400), t["note"], font=f("Regular", 13), fill=MUTED)
    d.text((48, 524), "github.com/CaiqueDourado", font=f("Regular", 14), fill=MUTED)
    im.save(OUT / f"cover{t['suffix']}.png")


def main() -> None:
    stats = json.loads((ROOT / "stats.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for lang, t in TEXT.items():
        chart(stats, lang, t)  # the cover is drawn by make_cover.py
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
