"""Builds docs/index.html: a static, interactive dashboard (Plotly) for GitHub Pages."""
from __future__ import annotations

import html
from pathlib import Path

import plotly.graph_objects as go
import plotly.offline

from . import metrics

ACCENT = "#e8743b"   # North Africa highlight
BASE = "#4a6fa5"
MUTED = "#9aa7b8"
PLOTLY_JS = f"https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{plotly.offline.get_plotlyjs_version()}/plotly.min.js"


def _layout(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=10, r=20, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color="#2b3440"),
        legend=dict(orientation="h", y=-0.18),
    )
    fig.update_xaxes(gridcolor="rgba(120,130,150,0.18)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(120,130,150,0.18)", zeroline=False)
    return fig


def fig_salary_by_country(t) -> go.Figure:
    t = t.sort_values("median")
    colors = [ACCENT if c.startswith("North Africa") else BASE for c in t["Country"]]
    names = [c.replace("United Kingdom of Great Britain and Northern Ireland", "United Kingdom")
              .replace("United States of America", "United States") for c in t["Country"]]
    fig = go.Figure(go.Bar(
        x=t["median"], y=names, orientation="h", marker_color=colors,
        error_x=dict(type="data", symmetric=False, array=t["q3"] - t["median"],
                     arrayminus=t["median"] - t["q1"], color="rgba(60,70,90,0.35)", thickness=1),
        customdata=t[["n", "q1", "q3"]],
        hovertemplate="%{y}<br>median $%{x:,.0f}<br>middle half $%{customdata[1]:,.0f}–$%{customdata[2]:,.0f}"
                      "<br>n = %{customdata[0]}<extra></extra>",
    ))
    fig.update_xaxes(title="Median yearly salary (USD); bars show the middle 50%", tickprefix="$")
    return _layout(fig, 700)


def fig_salary_by_experience(t) -> go.Figure:
    fig = go.Figure()
    for group, color in (("Worldwide", BASE), ("North Africa", ACCENT)):
        p = t[t["Group"] == group]
        fig.add_trace(go.Scatter(x=p["ExpBand"], y=p["median"], name=group, mode="lines+markers",
                                 line=dict(color=color, width=3), marker=dict(size=9), customdata=p["n"],
                                 hovertemplate=f"{group}<br>%{{x}}: $%{{y:,.0f}} (n = %{{customdata}})<extra></extra>"))
    fig.update_yaxes(title="Median yearly salary (USD)", tickprefix="$")
    return _layout(fig)


def fig_remote(t) -> go.Figure:
    t = t.sort_values("Remote")
    fig = go.Figure()
    for col, color in (("Remote", BASE), ("Hybrid", MUTED), ("In-person", "#c9d2dc")):
        fig.add_trace(go.Bar(y=t["Region"], x=t[col], name=col, orientation="h", marker_color=color,
                             customdata=t["n"],
                             hovertemplate=f"%{{y}}<br>{col}: %{{x:.1f}}% (n = %{{customdata}})<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Share of professional developers (%)", ticksuffix="%", range=[0, 100])
    return _layout(fig, 360)


def fig_ai(t) -> go.Figure:
    fig = go.Figure()
    for col, name, color in (("any_pct", "Uses AI tools", MUTED), ("favorable_pct", "Favorable view of AI", BASE),
                             ("daily_pct", "Uses AI daily", ACCENT)):
        fig.add_trace(go.Scatter(x=t["ExpBand"], y=t[col], name=name, mode="lines+markers",
                                 line=dict(color=color, width=3), marker=dict(size=9),
                                 hovertemplate=f"{name}<br>%{{x}}: %{{y:.1f}}%<extra></extra>"))
    fig.update_yaxes(title="% of professional developers", ticksuffix="%", range=[30, 100])
    return _layout(fig)


def fig_languages(t) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=t["used_pct"], y=t["admired_pct"], mode="markers+text", text=t["Language"].str.replace(" (all shells)", ""),
        textposition="top center", marker=dict(size=(t["users"] ** 0.5) / 4, color=BASE, opacity=0.75,
                                               line=dict(width=1, color="white")),
        customdata=t["users"],
        hovertemplate="%{text}<br>used by %{x:.1f}%<br>%{y:.1f}% want to keep using it"
                      "<br>%{customdata:,} users<extra></extra>",
    ))
    fig.update_xaxes(title="Used this year (% of respondents)", ticksuffix="%")
    fig.update_yaxes(title="Admired: users who want to keep using it", ticksuffix="%")
    return _layout(fig, 520)


def fig_na_languages(t) -> go.Figure:
    t = t.iloc[::-1]
    names = [n.replace(" (all shells)", "") for n in t.index]
    fig = go.Figure([
        go.Bar(y=names, x=t["Worldwide %"], name="Worldwide", orientation="h", marker_color=MUTED),
        go.Bar(y=names, x=t["North Africa %"], name="North Africa", orientation="h", marker_color=ACCENT),
    ])
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="Used this year (%)", ticksuffix="%")
    return _layout(fig, 480)


def _div(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def build(df, sal, out: Path, year: int) -> None:
    h = metrics.headline(df, sal)
    na = metrics.north_africa_spotlight(df, sal)
    tiles = [
        (f"{h['respondents']:,}", f"developers answered, from {h['countries']} countries"),
        (f"${h['median_salary_world']:,.0f}", "median yearly salary (USD), worldwide"),
        (f"{h['daily_ai_pct']}%", "of professional developers use AI tools every day"),
        (f"{na['daily_ai_pct']}%", f"of North African developers use AI daily, vs {na['daily_ai_pct_world']}% worldwide"),
    ]
    tiles_html = "".join(f'<div class="tile"><b>{html.escape(v)}</b><span>{html.escape(t)}</span></div>' for v, t in tiles)
    na_people = ", ".join(f"{c} {n}" for c, n in na["respondents"].items())

    sections = [
        ("Salary by country",
         f"Employed professional developers only. Countries with at least 50 salaries, plus North Africa pooled "
         f"(n = {na['salaries_n']}). The worldwide median is ${na['median_salary_world']:,.0f}; North Africa's is "
         f"${na['median_salary']:,.0f}.",
         fig_salary_by_country(metrics.salary_by_country(sal))),
        ("Salary grows with experience",
         "Median salary per experience band. North Africa only shows bands with at least 15 salaries; "
         "senior developers there are too few in the survey to chart honestly.",
         fig_salary_by_experience(metrics.salary_by_experience(sal))),
        ("Remote, hybrid or in-person",
         f"Western Europe is the most hybrid, North America the most remote. North Africa is more remote than "
         f"the world average ({na['remote_pct']}% vs {na['remote_pct_world']}%), which fits developers working "
         f"for companies abroad.",
         fig_remote(metrics.remote_by_region(df))),
        ("AI tools: juniors lead, everyone uses them",
         "Daily AI use falls steadily with experience, while overall use and favorable views stay high "
         "at every level.",
         fig_ai(metrics.ai_by_experience(df))),
        ("Used vs loved",
         "Popular isn't the same as loved: JavaScript is used by two thirds of developers but fewer than half "
         "want to keep using it, while Rust is the most admired language. Bubble size is the number of users.",
         fig_languages(metrics.languages(df))),
        ("North Africa's stack",
         f"{na['respondents_total']} respondents ({na_people}). Web technologies and PHP are more common than "
         f"worldwide, shell scripting less so.",
         fig_na_languages(na["top_languages"])),
    ]
    body = "".join(
        f'<section><h2>{html.escape(t)}</h2><p>{html.escape(d)}</p>{_div(f)}</section>' for t, d, f in sections
    )
    page = TEMPLATE.format(year=year, tiles=tiles_html, body=body, plotly_js=PLOTLY_JS,
                           salaries=f"{h['salaries_used']:,}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Developer Survey {year} Insights</title>
<meta name="description" content="What developers earn, where they work and how they use AI: an analysis of the Stack Overflow Developer Survey {year}, with a North Africa focus.">
<script src="{plotly_js}"></script>
<style>
:root {{ --bg:#f6f7f9; --card:#ffffff; --text:#2b3440; --muted:#667085; --accent:#e8743b; --line:#e4e7ec; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:Inter, "Segoe UI", system-ui, sans-serif; line-height:1.55; }}
header {{ padding:48px 16px 28px; max-width:1040px; margin:0 auto; }}
header p.kicker {{ color:var(--accent); font-weight:600; letter-spacing:.04em; text-transform:uppercase; font-size:13px; margin:0 0 8px; }}
h1 {{ font-size:clamp(28px, 5vw, 40px); margin:0 0 10px; line-height:1.15; }}
header p {{ color:var(--muted); max-width:720px; margin:0; }}
main {{ max-width:1040px; margin:0 auto; padding:0 16px 48px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:12px; margin-bottom:24px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }}
.tile b {{ display:block; font-size:28px; }}
.tile span {{ color:var(--muted); font-size:14px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:22px 20px 8px; margin-bottom:18px; }}
section h2 {{ margin:0 0 6px; font-size:20px; }}
section p {{ margin:0 0 8px; color:var(--muted); max-width:760px; }}
footer {{ max-width:1040px; margin:0 auto; padding:0 16px 48px; color:var(--muted); font-size:14px; }}
footer a {{ color:inherit; }}
</style>
</head>
<body>
<header>
  <p class="kicker">Stack Overflow Developer Survey {year}</p>
  <h1>What developers earn, where they work, and how they use AI</h1>
  <p>An analysis of the latest developer survey with a North Africa lens. Hover over any chart for exact numbers and sample sizes.</p>
</header>
<main>
<div class="tiles">{tiles}</div>
{body}
</main>
<footer>
  <p><b>Method.</b> Salaries: employed professional developers reporting a yearly salary converted to USD ({salaries} after cleaning).
  Salaries outside $1,000–$1,000,000 were dropped, then per-country outliers beyond 1.5× the interquartile range.
  Groups with small samples are pooled or hidden. Medians are used throughout because salaries are heavily skewed.</p>
  <p><b>Data.</b> <a href="https://survey.stackoverflow.co/">Stack Overflow Developer Survey {year}</a>, licensed under the
  <a href="https://opendatacommons.org/licenses/odbl/1-0/">Open Database License (ODbL)</a>. This is an independent analysis, not affiliated with Stack Overflow.</p>
</footer>
</body>
</html>
"""
