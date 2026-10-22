"""Profile the exported reviews and write small samples to send for review (runs locally, DuckDB).

    python -m pip install --user duckdb
    python perfil_reviews.py --raw D:\\reviews_raw          # writes D:\\reviews_raw\\_perfil\\ (send it zipped)

Outputs: counts and fill rate per column, value distributions of the short columns, length of the texts,
3,000 random reviews, 5,000 random sentences and every characteristic title. No personal columns exist
in the export, so the samples are safe to send.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    args = ap.parse_args()
    out = args.raw / "_perfil"
    out.mkdir(exist_ok=True)
    con = duckdb.connect()
    for table in ("reviews", "sentencas", "notas_caracteristicas", "caracteristicas_titulos"):
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{(args.raw / table).as_posix()}/*.parquet')")
    rows = []
    for table in ("reviews", "sentencas", "notas_caracteristicas"):
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for (col,) in con.execute(f"SELECT column_name FROM (DESCRIBE {table})").fetchall():
            filled, distinct = con.execute(
                f'SELECT count("{col}") FILTER (WHERE CAST("{col}" AS VARCHAR) <> \'\'), approx_count_distinct("{col}") FROM {table}').fetchone()
            rows.append((table, col, n, filled, distinct))
    con.execute("CREATE TABLE perfil (tabela VARCHAR, coluna VARCHAR, linhas BIGINT, preenchidas BIGINT, distintos BIGINT)")
    con.executemany("INSERT INTO perfil VALUES (?, ?, ?, ?, ?)", rows)
    con.execute(f"COPY perfil TO '{(out / 'colunas.csv').as_posix()}' (HEADER)")
    short = ["varejistaOrigem", "Rating", "RatingRange", "IsRecommended", "IsRatingsOnly", "ModerationStatus",
             "ContentLocale", "IsFeatured", "IsSyndicated", "CampaignId", "tipoVerificacao", "sentiment",
             "sentiment_original_aws_translate", "idTopico"]
    parts = [f"SELECT '{c}' AS coluna, CAST(\"{c}\" AS VARCHAR) AS valor, count(*) AS n FROM reviews GROUP BY 2" for c in short]
    con.execute(f"COPY (SELECT * FROM ({' UNION ALL '.join(parts)}) QUALIFY row_number() OVER (PARTITION BY coluna ORDER BY n DESC) <= 50 ORDER BY coluna, n DESC) TO '{(out / 'valores.csv').as_posix()}' (HEADER)")
    con.execute(f"""COPY (SELECT 'reviews' t, min(length(ReviewText)) mn, median(length(ReviewText)) md, max(length(ReviewText)) mx,
        min(SubmissionTime) primeiro, max(SubmissionTime) ultimo, min(dataGravacao) coleta_ini, max(dataGravacao) coleta_fim,
        count(*) FILTER (WHERE regexp_matches(ReviewText, '[\\w.+-]+@[\\w-]+\\.[\\w.]+')) com_email,
        count(*) FILTER (WHERE regexp_matches(ReviewText, '\\(?\\d{{2}}\\)?\\s?9?\\d{{4}}[-\\s]?\\d{{4}}')) com_telefone,
        count(*) FILTER (WHERE regexp_matches(ReviewText, '\\d{{3}}\\.?\\d{{3}}\\.?\\d{{3}}-?\\d{{2}}')) com_cpf
        FROM reviews) TO '{(out / 'textos.csv').as_posix()}' (HEADER)""")
    con.execute(f"COPY (SELECT * FROM reviews USING SAMPLE 3000 ROWS (reservoir, 42)) TO '{(out / 'amostra_reviews.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM sentencas USING SAMPLE 5000 ROWS (reservoir, 42)) TO '{(out / 'amostra_sentencas.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM caracteristicas_titulos) TO '{(out / 'caracteristicas_titulos.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT chave, count(*) n, avg(valor) media FROM notas_caracteristicas GROUP BY 1 ORDER BY 2 DESC LIMIT 300) TO '{(out / 'caracteristicas_top.csv').as_posix()}' (HEADER)")
    print("pronto:", out)


if __name__ == "__main__":
    main()
