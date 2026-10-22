# Methodology

How the reviews were collected (2017–2019), how the pros and cons were computed (2020), and how this release was built (2026).

![The five steps](img/flow.png)

## 1. Collection

The reviews come from the product pages of nine Brazilian stores. Most of them used **Bazaarvoice**, a review platform that serves each store's reviews as JSON (`reviews.json?Filter=ProductId:…&Include=Products,Authors…`):

| Store | Reviews | Source |
|---|---:|---|
| Americanas | 995,923 | Bazaarvoice (B2W) |
| Magazine Luiza | 776,168 | Bazaarvoice |
| Submarino | 545,574 | Bazaarvoice (B2W) |
| Shoptime | 236,499 | Bazaarvoice (B2W) |
| Casas Bahia | 143,038 | the store's own review API (Via Varejo) |
| Extra | 70,581 | the store's own review API (Via Varejo) |
| Leroy Merlin | 51,000 | Bazaarvoice |
| Ponto Frio | 42,055 | the store's own review API (Via Varejo) |
| Fast Shop | 10,258 | Bazaarvoice |

The collection started in 2017 for **É bom? Vale a pena?** ([opiniaobomvaleapena.com.br](https://web.archive.org/web/2022/https://opiniaobomvaleapena.com.br/)), a WordPress site of product reviews with one page per product ("<produto> é bom? vale a pena?") and affiliate links. Its database kept the Bazaarvoice layout. Later the same collection moved to the author's crawler and data lake (`CrawlerNewProductReview`), where each review was linked to the store offer it came from and to the catalog's product group, so reviews of the same product from different stores could be read together. The Via Varejo stores were collected in 2017–2018 through their own API, which does not return the Bazaarvoice fields (helpfulness, moderation, locale, campaign).

## 2. Pros and cons (2020)

The method, as the author presented it in "Divisão de Sentenças + Análise de sentimentos = Prós e Contras":

1. **Sentiment of each review.** Every review text was sent to **AWS Comprehend** (`DetectSentiment`, language `pt`), which answers POSITIVE, NEGATIVE, NEUTRAL or MIXED for the whole text. Only the label was stored. In May 2020 a check against the stars showed 59,005 reviews labelled POSITIVE with 1 or 2 stars; they were changed to NEGATIVE, and the AWS label kept in `sentiment_aws_original`. Other disagreements (NEGATIVE with 5 stars: "customers complain but don't want to give a bad grade") were left as they were. Empty texts and texts over Comprehend's 5,000-byte limit have no label (9,217).
2. **Part-of-speech tags.** The first version used Google Cloud Natural Language (`AnalyzeSyntax`); it was stopped on 9 Jan 2020 as too expensive. From then on, the **Stanford POS Tagger** (`MaxentTagger`, through Stanford.NLP.NET) with a third-party Portuguese model (`corenlp-model-pt`) tagged every word: `não/ADV`, `gaveta/NOUN`, `e/CONJ`. Before tagging, a period is added at the end, `/` is protected so "DANFE/XML" is not split, and punctuation glued to words is separated.
3. **Clauses.** The tagged text is cut at punctuation tokens and at conjunctions, except *que, se, como, quando, quanto, enquanto, apenas*, which stay inside the clause. "Não Recomendo, vão entre as gavetas e entre a gaveta e a estrutura…" becomes "Não Recomendo" / "vão entre as gavetas" / "Entre a gaveta" / "A estrutura"… Each clause is stored with the first letter in upper case and the rest in lower case (`text`) and with its tags in the original case (`tagged`). Store names inside reviews and clauses were replaced by "loja" (183,729 clauses in 171,672 reviews), clauses made of one repeated character ("kkkk", "!!!!") were deleted, and so were clauses over 300 characters.
4. **Group and count.** Each clause got six keys (Portuguese Metaphone, OpenRefine fingerprint, stems, sorted stems, character n-grams, soft normalisation; the same keyers as the [names dataset](https://github.com/CaiqueDourado/nomes-e-sobrenomes-brasil)). Inside each product group, clauses that share any key get one **canonical form**: the spelling that is most frequent in the whole database (`count_site`). Clauses with digits are matched only by the soft key, so "40Gb" and "70Gb" stay apart.
5. **Top 4.** For each product group, the canonical clauses with at least two words are counted separately in POSITIVE and in NEGATIVE reviews; the 4 most mentioned of each become the pros and the cons shown on the product page, ties broken by `count_site`.

The author's own note at the end of the grouping script reads "Abandonar aproximação por fingerprint": the fingerprint key could merge "produto de péssima qualidade" with "produto de ótima qualidade". See [data-quality.md](data-quality.md).

## 3. This release (2026)

`scripts/exportar_reviews.py` exports four tables to Parquet. The columns with personal data (`UserNickname`, `UserLocation`, `AuthorId`, `SubmissionId`, `IdReview` and the key made from them) are never selected, so they never leave the database. `scripts/build_reviews.py` then builds the dataset:

| Step | What it does | Rows |
|---|---|---:|
| Types | stars and counts as numbers, `True`/`False` as booleans, helpfulness with comma or period as a number | 2,871,096 reviews |
| Dates | two formats in the source: `dd/MM/yyyy HH:mm:ss` and `M/d/yyyy h:mm:ss AM`; all parsed | 0 failures |
| Personal data in the text | e-mails, phone numbers and CPF-like numbers replaced by `[e-mail]`, `[telefone]`, `[cpf]` | 76 · 226 · 168 masks |
| Lost ã/õ | see below | 815,816 texts, 1,571,552 words |
| Dropped columns | `Pros`, `Cons` (always empty), `RatingRange` (always 5), `ModerationStatus`, `tipoVerificacao`, `IsFeatured` (constant), internal ids | — |
| Clauses | renamed, store-name replacement kept, `normalizada_geral_todo_db` dropped (filled in 0.4%) | 12,896,607 |
| Aspect scores | the `Chave=Valor` pairs of the review form, with the 54 keys of different stores merged into 38 aspects in Portuguese | 2,484,634 |
| Pros and cons | recomputed from the exported clauses with the rule of step 5 | 922,402 rows, 222,976 products |
| Sample | every row of 2,000 random product groups, for GitHub | `sample/` |

**Lost ã/õ.** About 28% of the texts arrived without any ã or õ while keeping every other accent: "Ainda nao usei, a funçao é ótima". The writers did use accents, so the loss happened in collection. The build learns, from the texts that kept their ã/õ, which words are spelled with them (1,014 words, each seen at least 5 times and at least 5 times more often than its stripped form), and restores those words only in texts that have other accents and no ã/õ at all: "nao" → "não", "funçao" → "função", "mae" → "mãe". Texts with no accent at all are left as written. The original text is kept in `text_original`. The clauses were not changed.

`scripts/validate.py` checks the sample in CI; `scripts/docs.py` writes the data dictionaries and the Kaggle metadata from `schema/`.

## Joins

- `reviews.product_id` = `produtos.id` and `reviews.group_id` = `grupos.id` in the [catalog dataset](https://www.kaggle.com/datasets/caiquedourado/catalogo-produtos-ecommerce-brasil) (prices, specifications, EANs, categories).
- `groups` here already carries the product name of every group with reviews.
