"""Unit tests on small synthetic data (no download needed)."""
import pandas as pd
import pytest

from devsurvey import data, metrics


def make(rows):
    """Builds a cleaned survey-like frame from a list of dicts, filling unused columns."""
    base = {
        "Country": "Germany", "MainBranch": "I am a developer by profession", "Employment": "Employed",
        "WorkExp": 5.0, "RemoteWork": "Remote", "AISelect": "Yes, I use AI tools daily", "AISent": "Favorable",
        "ConvertedCompYearly": 60000.0, "LanguageHaveWorkedWith": "Python", "LanguageAdmired": "Python",
    }
    return data.clean(pd.DataFrame([{**base, **r} for r in rows]))


@pytest.mark.parametrize("country,region", [
    ("Tunisia", "North Africa"), ("Egypt", "North Africa"), ("Jordan", "Middle East"),
    ("Germany", "Western Europe"), ("Canada", "North America"), ("Japan", "Rest of world"), (float("nan"), "Unknown"),
])
def test_region_of(country, region):
    assert data.region_of(country) == region


@pytest.mark.parametrize("years,band", [(0, "0-2 yrs"), (2, "0-2 yrs"), (3, "3-5 yrs"), (10, "6-10 yrs"),
                                        (11, "11-20 yrs"), (35, "21+ yrs"), (float("nan"), None)])
def test_experience_band(years, band):
    assert data.experience_band(years) == band


def test_remote_group_collapses_the_five_answers():
    assert data.remote_group("Remote") == "Remote"
    assert data.remote_group("In-person") == "In-person"
    assert data.remote_group("Hybrid (some remote, leans heavy to in-person)") == "Hybrid"
    assert data.remote_group("Your choice (very flexible, you can come in when you want or just as needed)") == "Hybrid"
    assert data.remote_group(float("nan")) is None


def test_explode_multi_splits_and_skips_empty():
    s = pd.Series(["Python;SQL", None, "Rust", "Go;"])
    assert sorted(data.explode_multi(s)) == ["Go", "Python", "Rust", "SQL"]


def test_salary_sample_keeps_only_employed_professionals_in_bounds():
    df = make([
        {"ConvertedCompYearly": 50000},
        {"ConvertedCompYearly": 500},                  # below the sanity bound
        {"ConvertedCompYearly": 5_000_000},            # above the sanity bound
        {"ConvertedCompYearly": 60000, "Employment": "Student"},
        {"ConvertedCompYearly": 60000, "MainBranch": "I code primarily as a hobby"},
        {"ConvertedCompYearly": float("nan")},
    ])
    assert list(data.salary_sample(df)["ConvertedCompYearly"]) == [50000]


def test_salary_sample_drops_per_country_outliers():
    salaries = [50000, 52000, 54000, 56000, 58000, 60000, 62000, 64000, 900000]
    df = make([{"ConvertedCompYearly": s} for s in salaries])
    kept = data.salary_sample(df)["ConvertedCompYearly"].tolist()
    assert 900000 not in kept and len(kept) == 8


def test_languages_admired_rate():
    df = make([
        {"LanguageHaveWorkedWith": "Rust;Python", "LanguageAdmired": "Rust;Python"},
        {"LanguageHaveWorkedWith": "Rust;Python", "LanguageAdmired": "Rust"},
        {"LanguageHaveWorkedWith": "Python", "LanguageAdmired": None},
        {"LanguageHaveWorkedWith": "Python", "LanguageAdmired": None},
    ])
    t = metrics.languages(df, min_users=1).set_index("Language")
    assert t.loc["Rust", "admired_pct"] == 100.0      # 2 users, 2 admirers
    assert t.loc["Python", "admired_pct"] == 25.0     # 4 users, 1 admirer
    assert t.loc["Python", "used_pct"] == 100.0 and t.loc["Rust", "used_pct"] == 50.0


def test_salary_by_experience_hides_small_groups():
    rows = [{"Country": "Germany", "WorkExp": 4, "ConvertedCompYearly": 60000 + i} for i in range(20)]
    rows += [{"Country": "Tunisia", "WorkExp": 4, "ConvertedCompYearly": 10000 + i} for i in range(5)]
    t = metrics.salary_by_experience(data.salary_sample(make(rows)), min_n=15)
    assert set(t["Group"]) == {"Worldwide"}          # North Africa has only 5 salaries


def test_ai_by_experience_shares():
    df = make([
        {"WorkExp": 1, "AISelect": "Yes, I use AI tools daily", "AISent": "Favorable"},
        {"WorkExp": 1, "AISelect": "No, and I don't plan to", "AISent": "Unfavorable"},
        {"WorkExp": 25, "AISelect": "Yes, I use AI tools weekly", "AISent": "Very favorable"},
    ])
    t = metrics.ai_by_experience(df).set_index("ExpBand")
    assert t.loc["0-2 yrs", "daily_pct"] == 50.0 and t.loc["0-2 yrs", "any_pct"] == 50.0
    assert t.loc["21+ yrs", "daily_pct"] == 0.0 and t.loc["21+ yrs", "favorable_pct"] == 100.0


def test_salary_by_country_adds_pooled_north_africa():
    rows = [{"Country": "Germany", "ConvertedCompYearly": 60000 + i} for i in range(60)]
    rows += [{"Country": c, "ConvertedCompYearly": 12000} for c in ("Tunisia", "Morocco")]
    t = metrics.salary_by_country(data.salary_sample(make(rows)), min_n=50).set_index("Country")
    assert "North Africa (pooled)" in t.index and t.loc["North Africa (pooled)", "n"] == 2
    assert "Tunisia" not in t.index                  # too few on its own
