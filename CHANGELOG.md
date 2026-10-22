# Changelog

Versions follow [Semantic Versioning](https://semver.org/): a new major version renames or removes columns.

## [1.0.0] - 2026-10-22

### Added
- 2,871,096 reviews, 12,896,607 clauses, 2,484,634 aspect scores, pros and cons of 222,976 products and the names of 235,712 product groups (Parquet on Kaggle; a sample of 2,000 products in CSV here).
- Export, profile and build scripts; validation of the sample in GitHub Actions.
- Data dictionary (EN, PT), methodology, data quality report, figures, exploratory notebook, Kaggle metadata.

### Changed (relative to the author's database)
- Personal columns not exported; e-mails, phone numbers and CPF-like numbers masked; lost ã/õ restored in 815,816 texts (original kept); dates and numbers typed; constant columns dropped.
