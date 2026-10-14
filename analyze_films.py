"""
Cleans the Wikidata film exports and makes the summary tables and charts.
Usage: python analyze_films.py [in_dir] [out_dir] [chart_dir]

Year = earliest year listed for the film. Credits = unique film/director/gender
rows. Directors are matched by name only.
"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IN_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
OUT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data")
CHART_DIR = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

COUNTRIES = ["belgium", "portugal", "ireland"]
COLORS = {"Belgium": "#1f4e79", "Portugal": "#c0392b", "Ireland": "#2e8b57"}
MIN_GENDER_N = 20

C_ENG = "% with English label"
C_DIR = "% of films with a director recorded"
C_GEN = "% of director credits with gender recorded"
C_WOM = "% women among credits with known gender"
D_KNOWN = "Credits with known gender"
D_WOM = "% women (credits with known gender)"
D_SHARE = "Share of country's films (%)"


def load(country):
    path = IN_DIR / f"{country}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty:
        print(f"Skipping {country}: file has no data rows")
        return None
    df["qid"] = df["film"].str.extract(r"(Q\d+)$")
    return df


def clean_films(df):
    pairs = (df.dropna(subset=["directorLabel"])
               [["qid", "directorLabel", "genderLabel"]].drop_duplicates()
               .sort_values(["qid", "directorLabel", "genderLabel"], na_position="last")
               .reset_index(drop=True))
    films = df.groupby("qid").agg(
        title=("filmLabel", "first"),
        country=("countryLabel", "first"),
        first_year=("year", "min"),
        last_year=("year", "max"),
    ).reset_index()
    films["year_conflict"] = films["first_year"] != films["last_year"]
    films = films.drop(columns="last_year")
    films["decade"] = (films["first_year"] // 10) * 10
    films["has_english_label"] = ~films["title"].str.fullmatch(r"Q\d+")
    g = pairs.groupby("qid")
    films["directors"] = films["qid"].map(g["directorLabel"].agg("; ".join))
    films["director_genders"] = films["qid"].map(
        g["genderLabel"].agg(lambda s: "; ".join(s.fillna("unknown"))))
    films["has_director"] = films["directors"].notna()
    return films, pairs


def main():
    summary, decade_rows, store = [], [], {}
    for c in COUNTRIES:
        df = load(c)
        if df is None:
            continue
        films, pairs = clean_films(df)
        name = films["country"].iloc[0]
        films.to_csv(OUT_DIR / f"{c}_clean.csv", index=False)

        known = pairs.dropna(subset=["genderLabel"])
        summary.append({
            "Country": name,
            "Unique films": len(films),
            "Raw rows (before cleaning)": len(df),
            C_ENG: 100 * films["has_english_label"].mean(),
            C_DIR: 100 * films["has_director"].mean(),
            "Film-director credits": len(pairs),
            C_GEN: 100 * len(known) / len(pairs),
            C_WOM: 100 * (known["genderLabel"] == "female").mean(),
        })

        pairs = pairs.merge(films[["qid", "decade"]], on="qid")
        for d, n in films.groupby("decade").size().items():
            k = pairs[(pairs["decade"] == d) & pairs["genderLabel"].notna()]
            decade_rows.append({
                "Country": name, "Decade": int(d), "Films": n,
                D_SHARE: 100 * n / len(films),
                D_KNOWN: len(k),
                D_WOM: 100 * (k["genderLabel"] == "female").mean() if len(k) else None,
            })
        store[name] = (films, pairs)

    summary = pd.DataFrame(summary).round(1)
    by_decade = pd.DataFrame(decade_rows).round(1)
    summary.to_csv(OUT_DIR / "summary_by_country.csv", index=False)
    by_decade.to_csv(OUT_DIR / "summary_by_decade.csv", index=False)
    print(summary.T.to_string())

    fig, ax = plt.subplots(figsize=(9, 5))
    for name, g in by_decade.groupby("Country"):
        ax.plot(g["Decade"], g[D_SHARE], marker="o", label=name, color=COLORS.get(name))
    ax.set_title("What is catalogued? Share of each country's Wikidata films per decade")
    ax.set_xlabel("Decade (2020s is incomplete: data runs to 2026-27)")
    ax.set_ylabel("% of the country's films in Wikidata")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(CHART_DIR / "chart1_films_per_decade.png", dpi=160); plt.close(fig)

    cols = [C_ENG, C_DIR, C_GEN]
    ax = summary.set_index("Country")[cols].T.plot(
        kind="bar", figsize=(9, 5), rot=0,
        color=[COLORS.get(n) for n in summary["Country"]])
    ax.set_title("How complete is the record? Share of entries with each fact")
    ax.set_ylabel("%"); ax.set_ylim(0, 118); ax.grid(axis="y", alpha=0.3)
    ax.legend(title="Country", loc="upper center", ncol=len(summary))
    for cont in ax.containers:
        ax.bar_label(cont, fmt="%.0f%%", fontsize=8, padding=2)
    ax.set_xticklabels(["English label\n(per film)", "Director recorded\n(per film)",
                        "Director's gender recorded\n(per credit)"])
    ax.figure.tight_layout(); ax.figure.savefig(CHART_DIR / "chart2_completeness.png", dpi=160)
    plt.close(ax.figure)

    fig, ax = plt.subplots(figsize=(9, 5))
    all_decades = range(int(by_decade["Decade"].min()), int(by_decade["Decade"].max()) + 1, 10)
    for name, g in by_decade.groupby("Country"):
        g = g.set_index("Decade").reindex(all_decades)
        y = g[D_WOM].where(g[D_KNOWN] >= MIN_GENDER_N)
        ax.plot(g.index, y, marker="o", label=name, color=COLORS.get(name))
    ax.set_title("Women's share of director credits (known gender), by decade")
    ax.set_xlabel(f"Decade (only decades with at least {MIN_GENDER_N} credits with a recorded gender; 2020s incomplete)")
    ax.set_ylabel("% of credits"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(CHART_DIR / "chart3_women_directors.png", dpi=160); plt.close(fig)

    pivot = by_decade.pivot(index="Decade", columns="Country", values="Films").fillna(0)
    ax = pivot.plot(kind="bar", figsize=(10, 5), width=0.8,
                    color=[COLORS.get(c) for c in pivot.columns])
    ax.set_xticklabels([f"{int(d)}s" for d in pivot.index], rotation=45, ha="right")
    ax.set_title("Number of films in Wikidata per decade (raw counts)")
    ax.set_xlabel("Decade (2020s incomplete)"); ax.set_ylabel("Films"); ax.grid(axis="y", alpha=0.3)
    ax.figure.tight_layout(); ax.figure.savefig(CHART_DIR / "chart4_film_counts_per_decade.png", dpi=160)
    plt.close(ax.figure)

    fig, axes = plt.subplots(1, len(store), figsize=(5.5 * len(store), 6))
    axes = [axes] if len(store) == 1 else list(axes)
    for ax, (name, (films, pairs)) in zip(axes, store.items()):
        named = pairs[~pairs["directorLabel"].str.fullmatch(r"Q\d+")]
        top = named.groupby("directorLabel")["qid"].nunique().sort_values().tail(10)
        ax.barh(top.index, top.values, color=COLORS.get(name))
        ax.set_title(name); ax.set_xlabel("Films in Wikidata"); ax.grid(axis="x", alpha=0.3)
    fig.suptitle("Whose work is documented most? Ten most-recorded directors per country\n"
                 "(co-productions included; tied directors appear in arbitrary order)")
    fig.tight_layout(); fig.savefig(CHART_DIR / "chart5_top_directors.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
