"""Static PNG charts for the README (GitHub can't show the interactive dashboard inline)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

from . import metrics  # noqa: E402

ACCENT, BASE, MUTED = "#e8743b", "#4a6fa5", "#9aa7b8"


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)


def salary_by_country(t, path: Path) -> None:
    t = t.sort_values("median")
    names = [c.replace("United Kingdom of Great Britain and Northern Ireland", "United Kingdom")
              .replace("United States of America", "United States") for c in t["Country"]]
    fig, ax = plt.subplots(figsize=(8, 7.5), dpi=150)
    ax.barh(names, t["median"] / 1000, color=[ACCENT if n.startswith("North Africa") else BASE for n in names])
    ax.set_xlabel("Median yearly salary (thousand USD)")
    ax.set_title("Median developer salary by country", loc="left", fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def languages(t, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    ax.scatter(t["used_pct"], t["admired_pct"], s=t["users"] / 60, color=BASE, alpha=0.7, edgecolor="white")
    # labels that sit on top of each other get nudged apart (offset in points, alignment)
    nudge = {"Python": ((-8, 8), "right"), "SQL": ((8, 8), "left"),
             "Assembly": ((-6, 4), "right"), "Ruby": ((0, -12), "center")}
    for _, r in t.iterrows():
        offset, ha = nudge.get(r["Language"], ((0, 7), "center"))
        ax.annotate(r["Language"].replace(" (all shells)", ""), (r["used_pct"], r["admired_pct"]),
                    textcoords="offset points", xytext=offset, ha=ha, fontsize=8)
    ax.set_xlabel("Used this year (% of respondents)")
    ax.set_ylabel("Admired: want to keep using it (%)")
    ax.set_title("Used vs loved: programming languages", loc="left", fontweight="bold")
    _style(ax)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def ai_by_experience(t, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for col, name, color in (("any_pct", "Uses AI tools", MUTED), ("favorable_pct", "Favorable view", BASE),
                             ("daily_pct", "Uses AI daily", ACCENT)):
        ax.plot(t["ExpBand"], t[col], marker="o", linewidth=2.5, color=color, label=name)
    ax.set_ylim(30, 100)
    ax.set_ylabel("% of professional developers")
    ax.set_title("AI tool use by years of experience", loc="left", fontweight="bold")
    ax.legend(frameon=False)
    _style(ax)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def build(df, sal, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    salary_by_country(metrics.salary_by_country(sal), out_dir / "salary_by_country.png")
    languages(metrics.languages(df), out_dir / "languages.png")
    ai_by_experience(metrics.ai_by_experience(df), out_dir / "ai_by_experience.png")
