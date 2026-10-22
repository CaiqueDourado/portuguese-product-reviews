**Reviews de produtos (pt-BR) com prós e contras**: 2,87 milhões de avaliações de 9 lojas brasileiras, com sentimento, 12,9 milhões de cláusulas e os prós e contras de 222 mil produtos. **Brazilian product reviews** with sentiment, clauses and pros and cons per product.

![Pros and cons from reviews](https://raw.githubusercontent.com/CaiqueDourado/reviews-produtos-ptbr/main/docs/img/cover.png?v=2)

Reviews collected from 2017 to 2022 from the product pages of Americanas, Magazine Luiza, Submarino, Shoptime, Casas Bahia, Extra, Leroy Merlin, Ponto Frio and Fast Shop (written 2008–2019), for the author's review site *É bom? Vale a pena?* and data lake. About 22 times the size of B2W-Reviews01, the best-known Portuguese review dataset.

On top of the reviews, the 2020 pipeline that turned them into pros and cons:

![The five steps](https://raw.githubusercontent.com/CaiqueDourado/reviews-produtos-ptbr/main/docs/img/flow.png)

1. **Sentiment** of each review from AWS Comprehend.
2. **Part-of-speech tags** from the Stanford tagger (Portuguese model).
3. **Clauses** cut at punctuation and conjunctions.
4. **Grouped and counted** per product through six matching keys and a canonical form.
5. **Top 4 pros and 4 cons** per product.

## Files

- `reviews.parquet`: 2,871,096 reviews: stars, recommendation, title, text, AWS sentiment, helpfulness, dates, store.
- `sentences.parquet`: 12,896,607 clauses with POS tags, matching keys and canonical form.
- `aspect_ratings.parquet`: 2,484,634 scores per aspect (quality, design, battery, screen…).
- `pros_cons.parquet`: top 4 pros and 4 cons of 222,976 products.
- `groups.parquet`: product name, review count and average stars per product group.

`product_id` and `group_id` join with the [catalog of Brazilian e-commerce products](https://www.kaggle.com/datasets/caiquedourado/catalogo-produtos-ecommerce-brasil) (prices, specifications, EANs).

## Cleaning and privacy

Nicknames, cities and author ids were never exported. E-mails, phone numbers and CPF-like numbers inside the texts are masked. About 28% of the texts had lost every ã/õ in collection ("nao", "funçao"); those words were restored from intact texts and the original kept in `text_original`. Sentiment is per review, not per clause, so a cons list can contain a positive clause from a negative review: the data quality report explains this and the other limits.

Methodology, data quality report, data dictionary (EN and PT), build scripts and a sample: **https://github.com/CaiqueDourado/reviews-produtos-ptbr**. Starter notebook (sentiment × stars, aspects, pros and cons of one product): [notebook-reviews-produtos-ptbr](https://www.kaggle.com/code/caiquedourado/notebook-reviews-produtos-ptbr).

## Related

- [Catálogo de produtos do e-commerce brasileiro](https://www.kaggle.com/datasets/caiquedourado/catalogo-produtos-ecommerce-brasil)
- [Pares de produtos para matching](https://www.kaggle.com/datasets/caiquedourado/pares-matching-produtos-ptbr)
- [Nomes e sobrenomes do Brasil](https://www.kaggle.com/datasets/caiquedourado/nomes-e-sobrenomes-brasil) (same matching keys)
- [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr): Python library with the 2020 method and clause-level polarity (right cons 64.7% → 89.7%)
- [Case study: É bom? Vale a pena?](https://github.com/CaiqueDourado/reviews-produtos-ptbr/blob/main/docs/case-study-e-bom-vale-a-pena.md), the review site this data was collected for

License: CC BY 4.0 for the compilation and derived columns; review texts belong to their authors. Version 1.0.0. Author: Caique Dourado.
