"""The analyses. Each function returns a small tidy DataFrame (or dict) ready to chart."""
from __future__ import annotations

import pandas as pd

from .data import EXPERIENCE_BANDS, NORTH_AFRICA, explode_multi

BAND_ORDER = [label for _, _, label in EXPERIENCE_BANDS]
SENTIMENT_POSITIVE = {"Favorable", "Very favorable"}


def _quantiles(x: pd.Series) -> pd.Series:
    return pd.Series({"n": int(x.size), "median": x.median(), "q1": x.quantile(0.25), "q3": x.quantile(0.75)})


def salary_by_country(sal: pd.DataFrame, min_n: int = 50, top: int = 25) -> pd.DataFrame:
    """Median salary per country (countries with at least min_n salaries), plus a pooled
    North Africa row so the region can be compared even though each country is small."""
    by = sal.groupby("Country")["ConvertedCompYearly"].apply(_quantiles).unstack()
    by = by[by["n"] >= min_n].sort_values("n", ascending=False).head(top)
    na = _quantiles(sal.loc[sal["Country"].isin(NORTH_AFRICA), "ConvertedCompYearly"])
    by.loc["North Africa (pooled)"] = na
    by["n"] = by["n"].astype(int)
    return by.sort_values("median", ascending=False).reset_index(names="Country")


def salary_by_experience(sal: pd.DataFrame, min_n: int = 15) -> pd.DataFrame:
    """Median salary by experience band, worldwide vs North Africa. Bands with fewer than
    min_n salaries are left out rather than shown as a misleading median."""
    rows = []
    for label, part in (("Worldwide", sal), ("North Africa", sal[sal["Country"].isin(NORTH_AFRICA)])):
        for band in BAND_ORDER:
            x = part.loc[part["ExpBand"] == band, "ConvertedCompYearly"]
            if len(x) >= min_n:
                rows.append({"Group": label, "ExpBand": band, "n": len(x), "median": x.median()})
    return pd.DataFrame(rows)


def remote_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Share of Remote / Hybrid / In-person among professional developers, per region."""
    p = df[df["Professional"] & df["RemoteGroup"].notna() & (df["Region"] != "Unknown")]
    t = pd.crosstab(p["Region"], p["RemoteGroup"], normalize="index").mul(100).round(1)
    t["n"] = p.groupby("Region").size()
    return t.reset_index()


def ai_by_experience(df: pd.DataFrame) -> pd.DataFrame:
    """AI adoption and sentiment by experience band (professional developers)."""
    p = df[df["Professional"] & df["ExpBand"].notna() & df["AISelect"].notna()]
    g = p.groupby("ExpBand")
    out = pd.DataFrame({
        "n": g.size(),
        "daily_pct": g["DailyAI"].mean().mul(100),
        "any_pct": g["UsesAI"].mean().mul(100),
        "favorable_pct": g["AISent"].apply(lambda s: s.dropna().isin(SENTIMENT_POSITIVE).mean() * 100),
    }).reindex(BAND_ORDER).round(1)
    return out.reset_index()


def languages(df: pd.DataFrame, min_users: int = 1000, top: int = 20) -> pd.DataFrame:
    """Most used languages and their 'admiration' rate: of the people who used a language
    this year, the share who want to keep using it."""
    answered = df["LanguageHaveWorkedWith"].notna().sum()
    used = explode_multi(df["LanguageHaveWorkedWith"]).value_counts()
    admired = explode_multi(df["LanguageAdmired"]).value_counts()
    out = pd.DataFrame({"users": used, "admirers": admired}).fillna(0)
    out = out[out["users"] >= min_users]
    out["used_pct"] = (out["users"] / answered * 100).round(1)
    out["admired_pct"] = (out["admirers"] / out["users"] * 100).round(1)
    return out.sort_values("users", ascending=False).head(top).reset_index(names="Language")


def north_africa_spotlight(df: pd.DataFrame, sal: pd.DataFrame) -> dict:
    """Headline comparison between North Africa and everyone else."""
    na = df["Country"].isin(NORTH_AFRICA)
    prof = df["Professional"]
    na_lang = explode_multi(df.loc[na, "LanguageHaveWorkedWith"]).value_counts()
    na_lang_pct = (na_lang / df.loc[na, "LanguageHaveWorkedWith"].notna().sum() * 100).round(1)
    all_lang_pct = languages(df, min_users=1, top=500).set_index("Language")["used_pct"]
    top = na_lang_pct.head(10)
    na_sal = sal.loc[sal["Country"].isin(NORTH_AFRICA), "ConvertedCompYearly"]
    has_remote = df["RemoteGroup"].notna()
    is_remote = df["RemoteGroup"].eq("Remote")
    return {
        "respondents": df.loc[na, "Country"].value_counts().to_dict(),
        "respondents_total": int(na.sum()),
        "salaries_n": int(na_sal.size),
        "median_salary": float(na_sal.median()),
        "median_salary_world": float(sal["ConvertedCompYearly"].median()),
        "daily_ai_pct": round(float(df.loc[na & prof & df["AISelect"].notna(), "DailyAI"].mean() * 100), 1),
        "daily_ai_pct_world": round(float(df.loc[prof & df["AISelect"].notna(), "DailyAI"].mean() * 100), 1),
        "remote_pct": round(float(is_remote[na & prof & has_remote].mean() * 100), 1),
        "remote_pct_world": round(float(is_remote[prof & has_remote].mean() * 100), 1),
        "top_languages": pd.DataFrame({"North Africa %": top, "Worldwide %": all_lang_pct.reindex(top.index)}),
    }


def headline(df: pd.DataFrame, sal: pd.DataFrame) -> dict:
    prof = df[df["Professional"]]
    return {
        "respondents": int(len(df)),
        "countries": int(df["Country"].nunique()),
        "salaries_used": int(len(sal)),
        "median_salary_world": float(sal["ConvertedCompYearly"].median()),
        "daily_ai_pct": round(float(prof.loc[prof["AISelect"].notna(), "DailyAI"].mean() * 100), 1),
        "remote_pct": round(float(prof.loc[prof["RemoteGroup"].notna(), "RemoteGroup"].eq("Remote").mean() * 100), 1),
    }
