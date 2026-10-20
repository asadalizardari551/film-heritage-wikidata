# SPARQL queries

## Main export

The queries used to export the raw data in `data/raw/`, run on the Wikidata
Query Service (https://query.wikidata.org) on 9 October 2026.

- `belgium.rq`
- `portugal.rq`
- `ireland.rq`

They are identical except for the country on the `VALUES` line:
Belgium `wd:Q31`, Portugal `wd:Q45`, Ireland `wd:Q27`. None uses a LIMIT.

The files in `after/` are the same queries with one change: the label line is
`"en,mul"` instead of `"en"`. They were run on 9 October 2026 after my Wikidata
edits, and the results are in `data/raw_after/`.

## Benchmark queries

Used by `benchmark_belgium.py` to find out why some films that Cinema Belgica
tags Belgian are not in my Belgian export. The script writes each query for me
(a list of Wikidata IDs put into a template); I ran them by hand on
https://query.wikidata.org on 10 October 2026 and saved the results in
`data/benchmark/`. Both use `"en,mul"` labels.

- `diagnose_missing.rq`: for the 437 films not in my export, their type,
  country of origin and earliest publication date.
  Result: `data/benchmark/diagnose_missing.csv`.
- `diagnose_companies.rq`: for the 422 of those whose origin lists other
  countries, their production companies and the companies' countries.
  Result: `data/benchmark/diagnose_companies.csv`.
