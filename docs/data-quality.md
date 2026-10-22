# Data quality report

What is reliable, what was fixed, and what is still wrong. Counts are in `stats.json`.

## Know before using

- **Sentiment is per review, not per clause.** AWS Comprehend labelled the whole text, and every clause inherits that label. A NEGATIVE review that says "a entrega foi bem rápida, mas o produto é lento" puts "A entrega foi bem rápida" among the cons. In the sample, the notebook with most reviews (group 789660) has exactly that clause as its 3rd con, and a ladder has "Otimo produto" among its cons. This is the main limit of the 2020 method and the reason the [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr) library scores each clause. Labelled by hand on 51 products, 64.7% of the 2020 cons are right, 9.3% are on the wrong side and 26.0% carry no opinion; the library's are 89.7%, 2.5% and 7.8%.
- **Sentiment and stars disagree, by design of the labels.** 3-star reviews are 54% POSITIVE and 17% NEGATIVE; 5-star reviews still have 20,642 NEGATIVE labels. No 1–2 star review is POSITIVE because those were relabelled NEGATIVE in 2020 (`sentiment_aws_original` keeps the AWS label). Use `rating` when you need the customer's own judgement.

  ![Sentiment by stars](img/sentiment-by-rating.png)

- **The tagger makes mistakes, and the cuts follow them.** The Portuguese model is a third-party one and mislabels capitalised and colloquial words: `não/PNOUN Recomendo/PNOUN`, `gostei/NOUN`, `dão/ADP`, `aguenta/ADJ`. Only tokens tagged as punctuation or CONJ cut a clause, so a mistagged "e" does not cut and a mistagged word can. Clauses of one word ("Recomendo", "Infelizmente") are kept in `sentences` and ignored in `pros_cons`.
- **The canonical form can merge opposites.** Clauses that share *any* of six keys are grouped. The fingerprint key sorts words and, in the 2020 keyer, keeps only every other word (the bug documented in [DedupKit](https://github.com/CaiqueDourado/DedupKit)), so "Produto de péssima qualidade" and "Produto de ótima qualidade" can end with one canonical form. The author flagged it in 2020 and did not change it; the clauses are published as they were, `text` keeps each original.
- **Filler clauses reach the top 4.** The rule only asks for two words, so connectives cut out of a sentence count as opinions: the cons of "DVD Cinquenta Tons de Cinza" are *No mais · Ainda assim · O box · Desta forma*, and a ladder has *Boa noite* among its cons. Products with few negative reviews are the most affected.
- **`count_site` favours generic clauses.** It counts how often a clause appears in the whole database and breaks ties in favour of the most common, the opposite of IDF. "Muito bom", "Recomendo" and "Ótimo produto" win often.

## Fixed in this release

| # | Problem in the export | Rows | Fix |
|---|---|---:|---|
| 1 | Personal columns: nickname, city, author id, review ids | all | Not exported |
| 2 | E-mails, phone numbers and CPF-like numbers inside the text | 76 · 226 · 168 | Masked as `[e-mail]`, `[telefone]`, `[cpf]` |
| 3 | ã and õ lost in collection while other accents survived ("nao", "opçao", "padrao") | 815,816 texts | Restored from the spelling seen in intact texts; `text_original` keeps the collected text |
| 4 | Every column stored as text, dates in two formats, helpfulness with comma or period | all | Typed and parsed |
| 5 | `Pros` and `Cons` always empty; `RatingRange` always 5; `ModerationStatus`, `tipoVerificacao` constant; `IsFeatured` true once | all | Dropped |
| 6 | Aspect keys differ by store and language (`QualidadeGeral`, `Quality`; `Cmera` without the â) | 54 keys | `aspect` merges them into 38 names in Portuguese; `aspect_key` keeps the original |
| 7 | `normalizada_geral_todo_db` filled in 0.4% of the clauses | 48,955 | Dropped |

## Known limitations (kept as they are)

- **Store names were replaced in 2020, not always cleanly.** "Parabéns Americanas" became "parabéns", "na Magalu" became "na loja", but leftovers such as "loja.com" remain, and the `tagged` column was not updated, so store names can still appear there.
- **Clauses are in sentence case.** "Produto de BAIXA QUALIDADE" is stored as "Produto de baixa qualidade" in `text`; `tagged` keeps the original case.
- **Clauses were not restored.** The ã/õ restoration changed review texts only; clauses of those reviews keep "nao".
- **Missing metadata for three stores.** Casas Bahia, Extra and Ponto Frio (255,674 reviews) came from Via Varejo's own API: no helpfulness, feedback counts, locale, moderation or campaign.
- **Helpfulness is sparse.** Filled in 27% of the reviews.
- **No sentiment for 9,217 reviews** (empty or too long for Comprehend).
- **Dates.** Reviews run from December 2008 to December 2019; one review dated 2021 is probably a wrong date at the source. Collection by the author ran from 2017 to 2022.
- **Missing links.** 27 reviews have no `product_id` and 52 no `group_id`.
- **Text written by customers.** Besides the masked patterns, a review can still name a person or a place. Report it as an issue and it will be removed.
