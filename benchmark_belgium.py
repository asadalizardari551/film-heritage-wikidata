"""
Compares the Belgian export with Cinema Belgica (https://doi.org/10.7910/DVN/KZBIFY).
Usage: python benchmark_belgium.py [path/to/dataverse_files]

Needs data/belgium_clean.csv and dataverse_files/Film/tblFilm.csv. Without the
Cinema Belgica files only parts 3 and 4 run. Those two need Wikidata queries
run by hand; the script writes the query and stops if the CSV is missing.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CB_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataverse_files")
EXPORT = Path("data/belgium_clean.csv")
BENCH = Path("data/benchmark")
QUERIES = Path("queries")
CHART = Path("charts/chart6_benchmark_belgium.png")
MIN_N = 10

pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 45)
BENCH.mkdir(parents=True, exist_ok=True)
QUERIES.mkdir(parents=True, exist_ok=True)


def heading(text):
    print("\n" + "=" * 10, text, "=" * 10)


def split_pipe(s):
    return [t.strip() for t in s.split("|") if t.strip()]


def stop_for_query(name, qids, template, what):
    query_file = QUERIES / f"{name}.rq"
    query_file.write_text(
        template.replace("VALUES_HERE", " ".join(f"wd:{q}" for q in qids)),
        encoding="utf-8")
    print(f"\nMissing data/benchmark/{name}.csv ({what}).")
    print(f"Wrote {len(qids)} IDs to {query_file}")
    print(f"  1. Copy {query_file}")
    print("  2. Run it at https://query.wikidata.org")
    print("  3. Download as CSV")
    print(f"  4. Save it as data/benchmark/{name}.csv")
    print("  5. Run this script again")
    raise SystemExit


film_path = CB_ROOT / "Film" / "tblFilm.csv"
SAVED_MISSING = BENCH / "cb_belgian_with_qid_not_in_export.csv"

if film_path.exists():
    heading("PART 1: overlap with Cinema Belgica")

    if not EXPORT.exists():
        raise SystemExit(f"{EXPORT} not found, run analyze_films.py first")

    film = pd.read_csv(film_path, sep=None, engine="python", dtype=str,
                       encoding="utf-8", encoding_errors="replace")
    film["year"] = pd.to_numeric(film["film_year"], errors="coerce")
    film["qid"] = film["wikidata"].fillna("").str.strip()
    not_q = film["qid"].ne("") & ~film["qid"].str.fullmatch(r"Q\d+")
    print("non-empty Wikidata values that are not a clean Q-number:", not_q.sum())
    film.loc[film["qid"].eq("") | not_q, "qid"] = pd.NA
    is_bel = film["country"].fillna("").str.split("|").apply(lambda c: "BEL" in c)
    bel = film[is_bel].copy()

    mine = pd.read_csv(EXPORT)
    my_qids = set(mine["qid"])
    bel["has_qid"] = bel["qid"].notna()
    bel["in_export"] = bel["qid"].isin(my_qids)

    n_linked = int(bel["has_qid"].sum())
    n_found = int(bel["in_export"].sum())
    print("Belgian films in Cinema Belgica:", len(bel))
    print("  with a Wikidata ID:", n_linked, f"({100 * n_linked / len(bel):.1f}%)")
    print("  of those, found in the export:", n_found, f"({100 * n_found / n_linked:.1f}%)")
    print("Belgian films with no year:", int(bel["year"].isna().sum()))
    print("Belgian films year range:", bel["year"].min(), "-", bel["year"].max())

    bel["decade"] = bel["year"] // 10 * 10
    tab = bel.groupby("decade").agg(films=("film_id", "size"),
                                    linked=("has_qid", "sum"),
                                    found=("in_export", "sum"))
    print("\n", tab.to_string())

    missing = bel[bel["has_qid"] & ~bel["in_export"]]
    missing[["film_id", "title", "year", "country", "qid"]].to_csv(
        BENCH / "cb_belgian_with_qid_not_in_export.csv", index=False)
    print("\nsaved", len(missing), "films with an ID but not in the export")

    print("\nReverse check: Belgian films in the export up to 2019 -> anywhere in Cinema Belgica")
    cb_qids = set(film["qid"].dropna())
    old = mine[mine["first_year"] <= 2019]
    hit = old["qid"].isin(cb_qids)
    print("  films in the export up to 2019:", len(old))
    print("  found in Cinema Belgica by Wikidata ID:", int(hit.sum()),
          f"({100 * hit.mean():.1f}%)")

    heading("PART 2: chart")

    ctab = tab[tab["linked"] >= MIN_N].copy()
    ctab["share"] = 100 * ctab["found"] / ctab["linked"]
    overall = 100 * n_found / n_linked
    all_decades = list(range(int(tab.index.min()), int(tab.index.max()) + 1, 10))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([all_decades.index(int(d)) for d in ctab.index], ctab["share"], color="#1f4e79")
    for d, r in ctab.iterrows():
        ax.text(all_decades.index(int(d)), r["share"] + 1.5,
                f"{int(r['found'])}/{int(r['linked'])}", ha="center", fontsize=8)
    ax.axhline(overall, color="grey", linestyle="--", linewidth=1)
    ax.set_xticks(range(len(all_decades)))
    ax.set_xticklabels([f"{d}s" for d in all_decades])
    ax.set_ylim(0, 112)
    ax.set_ylabel("% of these films found in my Wikidata export")
    ax.set_xlabel(f"Decade (Cinema Belgica ends in 2019; decades with fewer than {MIN_N} "
                  "linked films are left empty)")
    ax.set_title("Does my export catch the films Cinema Belgica tags Belgian?\n"
                 f"Only films with a Wikidata ID in Cinema Belgica; labels show found/total; "
                 f"dashed line = all decades ({overall:.1f}%)", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    CHART.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART, dpi=160)
    plt.close(fig)
    print("saved", CHART)
elif SAVED_MISSING.exists():
    heading("PARTS 1 and 2 skipped")
    print(f"{film_path} not found, using {SAVED_MISSING}")
    missing = pd.read_csv(SAVED_MISSING, dtype=str)
else:
    raise SystemExit(f"{film_path} not found. Download Cinema Belgica first.")

heading("PART 3: why are the others missing?")

QUERY_DIAGNOSE = """SELECT ?film ?filmLabel
       (GROUP_CONCAT(DISTINCT ?typeLabel; SEPARATOR=" | ") AS ?types)
       (GROUP_CONCAT(DISTINCT ?originLabel; SEPARATOR=" | ") AS ?origins)
       (MIN(?date) AS ?first_date)
WHERE {
  VALUES ?film { VALUES_HERE }
  OPTIONAL { ?film wdt:P31 ?type. ?type rdfs:label ?typeLabel. FILTER(LANG(?typeLabel) = "en") }
  OPTIONAL { ?film wdt:P495 ?origin. ?origin rdfs:label ?originLabel. FILTER(LANG(?originLabel) = "en") }
  OPTIONAL { ?film wdt:P577 ?date. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}
GROUP BY ?film ?filmLabel
"""

src = BENCH / "diagnose_missing.csv"
if not src.exists():
    stop_for_query("diagnose_missing", missing["qid"].dropna().unique(),
                   QUERY_DIAGNOSE, "type, origin and date of the missing films")

wd = pd.read_csv(src, dtype=str).fillna("")
wd["qid"] = wd["film"].str.extract(r"(Q\d+)$")

cb = (missing[["film_id", "title", "year", "country", "qid"]]
      .rename(columns={"title": "cb_title", "year": "cb_year", "country": "cb_country"})
      .drop_duplicates("qid"))
df = cb.merge(wd, on="qid", how="left")
for c in ["film", "filmLabel", "types", "origins", "first_date"]:
    df[c] = df[c].fillna("")

types = df["types"].apply(split_pipe)
origins = df["origins"].apply(split_pipe)
df["is_film_type"] = types.apply(lambda t: "film" in t)
df["has_date"] = df["first_date"] != ""
df["has_origin"] = origins.apply(len) > 0
df["origin_belgium"] = origins.apply(lambda o: "Belgium" in o)

conds = [
    (df["types"] == "") & (df["origins"] == "") & (df["first_date"] == ""),
    ~df["is_film_type"],
    ~df["has_date"],
    ~df["has_origin"],
    ~df["origin_belgium"],
]
labels = [
    "1 no statements at all (redirect, deleted or empty item)",
    "2 not typed exactly as 'film' (short, documentary...)",
    "3 no publication date",
    "4 no country of origin",
    "5 origin lists other countries, not Belgium",
]
df["reason"] = np.select(conds, labels, default="6 matches every filter (unexpected)")

print(len(df), "films (unique Wikidata IDs) are not in the export:\n")
print(df["reason"].value_counts().sort_index().to_string())

df["cb_year_n"] = pd.to_numeric(df["cb_year"], errors="coerce")
df["wd_year"] = pd.to_numeric(df["first_date"].str[:4], errors="coerce")
df["cb_decade"] = df["cb_year_n"] // 10 * 10
print("\nBy Cinema Belgica decade (columns = reason number):")
print(pd.crosstab(df["cb_decade"], df["reason"].str[0]).to_string())

gap = (df["cb_year_n"] - df["wd_year"]).abs()
known = gap.notna()
agree = int((gap <= 1).sum())
print("\nIs the ID link plausible? Year in Cinema Belgica vs Wikidata:")
print("  films with both years:", int(known.sum()))
print("  years agree within 1 year:", agree, f"({100 * agree / max(int(known.sum()), 1):.0f}%)")

print("\nSample of reason 5:")
print(df[df["reason"].str.startswith("5")][
    ["cb_title", "cb_year", "cb_country", "filmLabel", "wd_year", "origins"]
].head(15).to_string())

df.to_csv(BENCH / "diagnosis_result.csv", index=False)
print("\nsaved data/benchmark/diagnosis_result.csv")

heading("PART 4: is a Belgian production company recorded?")

QUERY_COMPANIES = """SELECT ?film ?filmLabel
       (GROUP_CONCAT(DISTINCT ?coLabel; SEPARATOR=" | ") AS ?companies)
       (GROUP_CONCAT(DISTINCT ?ccLabel; SEPARATOR=" | ") AS ?company_countries)
WHERE {
  VALUES ?film { VALUES_HERE }
  OPTIONAL {
    ?film wdt:P272 ?co.
    OPTIONAL { ?co rdfs:label ?coLabel. FILTER(LANG(?coLabel) = "en") }
    OPTIONAL { ?co wdt:P17 ?cc. ?cc rdfs:label ?ccLabel. FILTER(LANG(?ccLabel) = "en") }
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}
GROUP BY ?film ?filmLabel
"""

diag = df[df["reason"].str.startswith("5")].copy()
src2 = BENCH / "diagnose_companies.csv"
if not src2.exists():
    stop_for_query("diagnose_companies", diag["qid"].dropna().unique(),
                   QUERY_COMPANIES, "production companies of the reason-5 films")

co = pd.read_csv(src2, dtype=str).fillna("")
co["qid"] = co["film"].str.extract(r"(Q\d+)$")
d5 = diag.merge(co[["qid", "companies", "company_countries"]], on="qid", how="left")
d5[["companies", "company_countries"]] = d5[["companies", "company_countries"]].fillna("")

has_company = d5["companies"] != ""
belgian_co = d5["company_countries"].apply(split_pipe).apply(lambda c: "Belgium" in c)
unknown_country = has_company & (d5["company_countries"] == "")
d5["company_status"] = np.select(
    [belgian_co, ~has_company, unknown_country],
    ["A Belgian production company recorded",
     "C no production company recorded",
     "B1 companies recorded, but none has a country"],
    default="B2 companies recorded, none of them Belgian",
)

print("The", len(d5), "films with other origin countries (reason 5):")
print("rows returned by the Wikidata query:", len(co), "\n")
print(d5["company_status"].value_counts().sort_index().to_string())

print("\nBy decade:")
print(pd.crosstab(d5["cb_decade"], d5["company_status"].str.split().str[0]).to_string())

cols = ["cb_title", "cb_year", "origins", "companies"]
print("\nSample: Belgian company recorded (A)")
print(d5[d5["company_status"].str.startswith("A")][cols].head(10).to_string())
print("\nSample: no production company recorded (C)")
print(d5[d5["company_status"].str.startswith("C")][cols].head(10).to_string())

d5.to_csv(BENCH / "company_result.csv", index=False)
print("\nsaved data/benchmark/company_result.csv")
print("\nDone.")
