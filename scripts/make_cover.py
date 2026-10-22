"""Cover (1120x560): three real reviews go into the pipeline, the clauses come out as top pros and cons.

    python scripts/make_cover.py         # docs/img/cover.png and cover.pt-BR.png

Reviews and output are real: product group 725383 in the sample.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
INK, MUTED, LINE, BG = "#111111", "#5a5a5a", "#c9d1db", "#fdfdfc"
POS, NEG = "#2a78d6", "#d6452a"
REVIEWS = [  # (stars, sentiment, text, clauses)
    (5, "POSITIVE", "Ótimo produto, ideal para idosos. Entrega rápida, recomendo.",
     ["Ótimo produto", "Ideal para idosos", "Entrega rápida", "Recomendo"]),
    (1, "NEGATIVE", "Aparelho nao suporta 30 min fora do carregador, trava muito, aquece demasiadamente.",
     ["Aparelho nao suporta 30 min fora do carregador", "Trava muito", "Aquece demasiadamente"]),
    (1, "NEGATIVE", "Produto demorou a chegar e veio com defeito",
     ["Produto demorou a chegar", "Veio com defeito"]),
]
PROS = ["Muito bom", "Fácil de usar", "Ela adorou", "Entrega rápida"]
CONS = ["Nao recomendo", "Veio com defeito", "Péssimo produto", "Trava muito"]
TEXT = {
    "en": {"suffix": "", "title": "Product reviews with pros and cons",
           "sub": "2,871,096 reviews · 9 Brazilian stores · 12.9 M clauses · pros and cons of 222,976 products",
           "in": "Reviews in", "machine": "Clauses", "steps": "sentiment · POS tags · cut · group and count",
           "pros": "Top pros", "cons": "Top cons", "more": "… and 798 more reviews of the same product",
           "rule": "clauses of POSITIVE reviews → pros · of NEGATIVE reviews → cons",
           "note": "Real reviews and output: Samsung Galaxy Gran 2 Duos, 801 reviews"},
    "pt": {"suffix": ".pt-BR", "title": "Reviews de produtos com prós e contras",
           "sub": "2.871.096 reviews · 9 lojas brasileiras · 12,9 mi cláusulas · prós e contras de 222.976 produtos",
           "in": "Entram reviews", "machine": "Cláusulas", "steps": "sentimento · etiquetas · corte · agrupar e contar",
           "pros": "Principais prós", "cons": "Principais contras", "more": "… e mais 798 reviews do mesmo produto",
           "rule": "reviews POSITIVE → prós · reviews NEGATIVE → contras",
           "note": "Reviews e resultado reais: Samsung Galaxy Gran 2 Duos, 801 reviews"},
}


def font(weight: str, size: int):
    return ImageFont.truetype(FONT.format(weight), size)


def wrap(d, text, f, width):
    lines, line = [], ""
    for w in text.split():
        test = (line + " " + w).strip()
        if d.textlength(test, font=f) > width and line:
            lines.append(line)
            line = w
        else:
            line = test
    return lines + [line]


def curve(d, a, b, color, width=2):
    (x0, y0), (x1, y1) = a, b
    pts = []
    for i in range(31):
        t = i / 30
        cx0, cx1 = x0 + (x1 - x0) * 0.5, x0 + (x1 - x0) * 0.5
        x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * cx0 + 3 * (1 - t) * t ** 2 * cx1 + t ** 3 * x1
        y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y0 + 3 * (1 - t) * t ** 2 * y1 + t ** 3 * y1
        pts.append((x, y))
    d.line(pts, fill=color, width=width)
    d.polygon([(x1, y1), (x1 - 9, y1 - 5), (x1 - 9, y1 + 5)], fill=color)


def draw(t: dict) -> None:
    im = Image.new("RGB", (1120, 560), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 26), t["title"], font=font("Bold", 34), fill=INK)
    d.text((40, 74), t["sub"], font=font("Regular", 15), fill=MUTED)

    # reviews (left)
    d.text((40, 118), t["in"], font=font("SemiBold", 13), fill=MUTED)
    ys, anchors = [140, 262, 384], []
    body = font("Regular", 13)
    for (stars, sent, text, _), y in zip(REVIEWS, ys):
        color = POS if sent == "POSITIVE" else NEG
        lines = wrap(d, text, body, 236)
        h = 34 + 18 * len(lines)
        d.rounded_rectangle((40, y, 300, y + h), radius=8, fill="#ffffff", outline=LINE)
        d.text((52, y + 9), "★" * stars + "☆" * (5 - stars), font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13), fill="#e0a100")
        tw = d.textlength(sent, font=font("SemiBold", 11))
        d.text((288 - tw, y + 10), sent, font=font("SemiBold", 11), fill=color)
        for i, line in enumerate(lines):
            d.text((52, y + 30 + 18 * i), line, font=body, fill=INK)
        anchors.append((300, y + h / 2, color))

    # machine (middle)
    mx0, my0, mx1, my1 = 372, 128, 742, 500
    d.rounded_rectangle((mx0, my0, mx1, my1), radius=14, fill="#f3f5f8", outline="#9aa5b1", width=2)
    d.text((mx0 + 18, my0 + 12), t["machine"], font=font("Bold", 18), fill=INK)
    d.text((mx0 + 18, my0 + 38), t["steps"], font=font("Regular", 12), fill=MUTED)
    y, chip = my0 + 66, font("Regular", 12)
    for stars, sent, _, clauses in REVIEWS:
        color = POS if sent == "POSITIVE" else NEG
        x = mx0 + 18
        for c in clauses:
            w = d.textlength(c, font=chip) + 16
            if x + w > mx1 - 16:
                x, y = mx0 + 18, y + 30
            d.rounded_rectangle((x, y, x + w, y + 22), radius=11, fill="#ffffff", outline=color)
            d.text((x + 8, y + 4), c, font=chip, fill=INK)
            x += w + 6
        y += 40
    d.text((mx0 + 18, my1 - 66), t["more"], font=font("Regular", 13), fill=MUTED)
    d.text((mx0 + 18, my1 - 44), t["rule"], font=font("Regular", 12), fill=MUTED)
    for x, yy, color in anchors:
        curve(d, (x + 4, yy), (mx0 - 2, min(max(yy, my0 + 40), my1 - 40)), color)

    # outputs (right)
    for (title, items, color, fill, y0) in ((t["pros"], PROS, POS, "#e7f1fb", 128), (t["cons"], CONS, NEG, "#fbebeb", 322)):
        d.rounded_rectangle((812, y0, 1080, y0 + 178), radius=12, fill=fill)
        d.text((828, y0 + 12), title, font=font("Bold", 16), fill=color)
        for i, item in enumerate(items, 1):
            d.text((828, y0 + 44 + 31 * i - 31), f"{i}  {item}", font=font("Regular", 15), fill=INK)
        curve(d, (mx1 + 2, (my0 + my1) / 2), (810, y0 + 89), color, 3)

    d.text((40, 528), t["note"], font=font("Regular", 12), fill=MUTED)
    tw = d.textlength("github.com/CaiqueDourado", font=font("Regular", 12))
    d.text((1080 - tw, 528), "github.com/CaiqueDourado", font=font("Regular", 12), fill=MUTED)
    im.save(ROOT / "docs" / "img" / f"cover{t['suffix']}.png")


if __name__ == "__main__":
    for t in TEXT.values():
        draw(t)
    print("covers written")
