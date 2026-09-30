"""Downloading, loading and cleaning the Stack Overflow Developer Survey."""
from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

SURVEY_URL = "https://github.com/StackExchange/Survey/raw/refs/heads/main/packages/archive/{year}/results.csv"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

NORTH_AFRICA = ["Tunisia", "Morocco", "Algeria", "Egypt", "Libya"]
MIDDLE_EAST = [
    "Jordan", "Lebanon", "Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait", "Bahrain",
    "Oman", "Iraq", "Syrian Arab Republic", "Palestine", "Yemen",
]
EUROPE_WEST = [
    "Germany", "France", "United Kingdom of Great Britain and Northern Ireland", "Netherlands",
    "Spain", "Italy", "Belgium", "Switzerland", "Austria", "Sweden", "Denmark", "Norway",
    "Finland", "Ireland", "Portugal",
]
NORTH_AMERICA = ["United States of America", "Canada"]

# Salary sanity bounds in USD per year, applied before the per-country outlier filter
MIN_SALARY, MAX_SALARY = 1_000, 1_000_000

EXPERIENCE_BANDS = [(0, 2, "0-2 yrs"), (3, 5, "3-5 yrs"), (6, 10, "6-10 yrs"),
                    (11, 20, "11-20 yrs"), (21, 200, "21+ yrs")]


def download(year: int = 2025, force: bool = False) -> Path:
    """Downloads the raw survey CSV (ODbL licensed) into data/ unless it is already there."""
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"survey_{year}.csv"
    if force or not path.exists():
        print(f"Downloading the {year} survey (about 140 MB)...")
        urllib.request.urlretrieve(SURVEY_URL.format(year=year), path)
    return path


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
    df.columns = [c.strip().strip('"') for c in df.columns]
    return df


def region_of(country: str | float) -> str:
    if not isinstance(country, str):
        return "Unknown"
    if country in NORTH_AFRICA:
        return "North Africa"
    if country in MIDDLE_EAST:
        return "Middle East"
    if country in EUROPE_WEST:
        return "Western Europe"
    if country in NORTH_AMERICA:
        return "North America"
    return "Rest of world"


def experience_band(years: float) -> str | None:
    if pd.isna(years):
        return None
    for lo, hi, label in EXPERIENCE_BANDS:
        if lo <= years <= hi:
            return label
    return None


def remote_group(value: str | float) -> str | None:
    """Collapses the five remote-work answers into Remote / Hybrid / In-person."""
    if not isinstance(value, str):
        return None
    if value.startswith("Remote"):
        return "Remote"
    if value.startswith("In-person"):
        return "In-person"
    return "Hybrid"  # both hybrid answers and "your choice" (very flexible)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Adds the derived columns every analysis uses. Rows are not dropped here."""
    out = df.copy()
    out["Region"] = out["Country"].map(region_of)
    out["ExpBand"] = out["WorkExp"].map(experience_band)
    out["RemoteGroup"] = out["RemoteWork"].map(remote_group)
    out["Professional"] = out["MainBranch"].eq("I am a developer by profession")
    out["DailyAI"] = out["AISelect"].eq("Yes, I use AI tools daily")
    out["UsesAI"] = out["AISelect"].fillna("").str.startswith("Yes")
    return out


def salary_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Employed professional developers with a plausible yearly salary in USD.

    Two filters, both documented in the README:
      1. drop salaries outside MIN_SALARY..MAX_SALARY (typos, monthly entered as yearly, ...)
      2. drop per-country outliers outside Tukey's fences (1.5 x IQR)
    """
    s = df[df["Professional"] & df["Employment"].eq("Employed")].copy()
    s = s[s["ConvertedCompYearly"].between(MIN_SALARY, MAX_SALARY)]
    q1 = s.groupby("Country")["ConvertedCompYearly"].transform(lambda x: x.quantile(0.25))
    q3 = s.groupby("Country")["ConvertedCompYearly"].transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1
    keep = s["ConvertedCompYearly"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return s[keep]


def explode_multi(series: pd.Series) -> pd.Series:
    """Splits a ';'-separated multi-select column into one value per row (index kept)."""
    return series.dropna().str.split(";").explode().str.strip().loc[lambda x: x != ""]
