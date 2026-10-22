# Dicionário de dados: Reviews de produtos do e-commerce brasileiro com sentimento, cláusulas e prós e contras

Gerado por `scripts/docs.py` a partir de `schema/columns.json`. Nulos e exemplos vêm da amostra em `sample/`.

## `reviews`

2.871.096 reviews de 9 lojas brasileiras (2008-2019): estrelas, texto, sentimento AWS, utilidade.

| Coluna | Tipo | Nulos | Exemplo | Descrição |
|---|---|---|---|---|
| `review_id` | integer | 0,0% | `3925753` | Id do review no banco do autor. Chave primária. |
| `product_id` | integer | 0,0% | `2693916` | Oferta de onde o review foi coletado: `produtos.id` na base do catálogo. |
| `group_id` | integer | 0,0% | `601133` | Grupo de produto (o mesmo produto em várias lojas): `grupos.id` no catálogo e chave de groups e pros_cons. |
| `store` | string | 0,0% | `Shoptime` | Loja em cuja página do produto o review aparecia. |
| `rating` | integer | 0,0% | `3` | Estrelas dadas pelo cliente, de 1 a 5. |
| `recommended` | boolean | 19,0% | `true` | Se o cliente respondeu sim a "você recomendaria este produto?". Vazio quando não foi perguntado. |
| `ratings_only` | boolean | 7,4% | `false` | Review só com estrelas, sem texto, segundo a plataforma de reviews. |
| `title` | string | 38,6% | `Muiiito bom` | Título do review escrito pelo cliente. |
| `text` | string | 0,3% | `Gostei porque é muito útil, durável e…` | Texto do review. Nomes de lojas trocados por "loja" em 2020; e-mails, telefones e CPFs mascarados; ã/õ perdidos restaurados (ver text_original). |
| `text_original` | string | 69,1% | `A Escada Multifuncional Articulada 4x…` | Texto como coletado, só quando a restauração de ã/õ o alterou. |
| `tilde_restored` | boolean | 0,0% | `false` | Verdadeiro quando ã/õ foram restaurados em `text`. |
| `sentiment` | string | 0,3% | `NEGATIVE` | Sentimento do review inteiro pelo AWS Comprehend (POSITIVE, NEGATIVE, NEUTRAL, MIXED); POSITIVE com 1-2 estrelas virou NEGATIVE em 2020. |
| `sentiment_aws_original` | string | 97,8% | `POSITIVE` | Rótulo da AWS antes dessa troca (só nas linhas trocadas). |
| `helpfulness` | float | 67,1% | `0.52381` | Proporção de leitores que acharam o review útil, de 0 a 1, como publicado pela plataforma. |
| `feedback_positive` | integer | 7,4% | `0` | Leitores que marcaram o review como útil. |
| `feedback_negative` | integer | 7,4% | `0` | Leitores que marcaram o review como não útil. |
| `comments` | integer | 7,4% | `0` | Comentários no review. |
| `submitted_at` | timestamp | 0,0% | `2018-03-12 19:20:26` | Quando o cliente enviou o review. |
| `modified_at` | timestamp | 7,4% | `2018-01-09 11:16:10` | Última alteração na plataforma. |
| `locale` | string | 7,4% | `pt_BR` | Idioma e país do review (pt_BR em 99,9% dos que têm). |
| `syndicated` | boolean | 7,4% | `false` | Review compartilhado de outro site da mesma rede de reviews, segundo a plataforma. |
| `campaign` | string | 40,4% | `BV_RATING_SUMMARY` | Onde o review foi coletado (e-mail pós-compra, página do produto, app...), segundo a plataforma. |
| `collected_at` | timestamp | 0,0% | `2019-12-01 02:35:52.287` | Quando o crawler do autor gravou o review. |

## `sentences`

12.896.607 cláusulas cortadas dos reviews pelo método de 2020 (etiquetas Stanford), com chaves e forma canônica.

| Coluna | Tipo | Nulos | Exemplo | Descrição |
|---|---|---|---|---|
| `sentence_id` | integer | 0,0% | `6530809` | Id da cláusula. Chave primária. |
| `review_id` | integer | 0,0% | `3877164` | Review de onde a cláusula saiu. |
| `group_id` | integer | 0,0% | `740351` | Grupo de produto do review. |
| `text` | string | 0,0% | `Idiomas audio Português 5.1 dd` | A cláusula, cortada em pontuação e conjunções pelo método de 2020; primeira letra maiúscula, resto minúsculo. |
| `tagged` | string | 0,0% | `Idiomas/NOUN audio/NOUN Português/PNO…` | A cláusula com as etiquetas do Stanford POS Tagger (`palavra/TAG`), caixa original. |
| `canonical` | string | 0,0% | `Espanhol 5.1 dd` | Forma canônica dentro do grupo: a grafia mais frequente entre as cláusulas que compartilham uma chave. É a coluna exibida como pró/contra. |
| `count_site` | integer | 0,0% | `1` | Quantas vezes a mesma cláusula aparece no banco inteiro (todos os produtos e lojas). |
| `key_metaphone` | string | 11,8% | `PKELPGKR` | Metaphone português da cláusula (vazio para cláusula de uma palavra). |
| `key_fingerprint` | string | 57,1% | `comprar de na` | Fingerprint do OpenRefine, com o bug do keyer (guarda uma palavra sim, outra não); vazio com menos de 3 palavras. |
| `key_tokens` | string | 45,7% | `sinal digital pessim` | Sem stopwords e com o stemmer brasileiro; vazio com menos de 3 palavras. |
| `key_tokens_fingerprint` | string | 45,7% | `digital pessim sinal` | Os radicais de key_tokens, ordenados. |
| `key_ngram` | string | 0,0% | `1 5 a d p1 5 asaudddiesguidiomao omor…` | Fingerprint de 2-gramas de caracteres. |
| `key_soft` | string | 0,0% | `espanhol 51 dd` | Minúsculas, sem acento, só letras, dígitos e espaços. |

## `aspect_ratings`

2.484.634 notas por aspecto (qualidade, design, bateria...) dadas nos reviews.

| Coluna | Tipo | Nulos | Exemplo | Descrição |
|---|---|---|---|---|
| `review_id` | integer | 0,0% | `4732306` | Review a que a nota pertence. |
| `aspect_key` | string | 0,0% | `Facilidadedemontagem` | Chave do aspecto como o formulário da loja a chamava (QualidadeGeral, Design2, BatteryLife...). |
| `aspect` | string | 0,0% | `Facilidade de Montagem` | Aspecto em português, com as chaves das lojas unificadas (Qualidade, Design, Bateria...). |
| `score` | integer | 0,0% | `3` | Nota dada ao aspecto, de 1 a 5. |

## `pros_cons`

Os 4 prós e 4 contras de 222.976 produtos, calculados com a regra de 2020.

| Coluna | Tipo | Nulos | Exemplo | Descrição |
|---|---|---|---|---|
| `group_id` | integer | 0,0% | `1453062` | Grupo de produto. |
| `kind` | string | 0,0% | `pro` | `pro` (de reviews POSITIVE) ou `con` (de reviews NEGATIVE). |
| `rank` | integer | 0,0% | `4` | De 1 a 4, como exibido na página do produto. |
| `clause` | string | 0,0% | `A empresa peça apenas nas fotos` | Cláusula canônica com pelo menos duas palavras. |
| `mentions` | integer | 0,0% | `1` | Cláusulas do grupo e sentimento com essa forma canônica (1ª chave de ordenação). |
| `count_site` | integer | 0,0% | `1` | Frequência da cláusula no banco inteiro (desempate). |
| `example_review_id` | integer | 0,0% | `4033330` | Um review que contém a cláusula. |

## `groups`

Nome, quantidade de reviews e média de estrelas de cada grupo de produto.

| Coluna | Tipo | Nulos | Exemplo | Descrição |
|---|---|---|---|---|
| `group_id` | integer | 0,0% | `1741525` | Grupo de produto. Chave primária. |
| `group_name` | string | 0,1% | `Kit Higiene Provence com 5 Peças Quar…` | Nome do produto do grupo no catálogo. |
| `reviews` | integer | 0,0% | `1` | Reviews do grupo nesta base. |
| `avg_rating` | float | 0,0% | `5.0` | Média de estrelas desses reviews. |
