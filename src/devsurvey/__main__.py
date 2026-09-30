"""python -m devsurvey [--year 2025] : download, analyse, and build the dashboard + charts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import charts, dashboard, data, metrics

DOCS = Path(__file__).resolve().parents[2] / "docs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()

    df = data.clean(data.load(data.download(args.year)))
    sal = data.salary_sample(df)

    dashboard.build(df, sal, DOCS / "index.html", args.year)
    charts.build(df, sal, DOCS / "img")

    h = metrics.headline(df, sal)
    na = metrics.north_africa_spotlight(df, sal)
    summary = {**h, "north_africa": {k: v for k, v in na.items() if k != "top_languages"}}
    (DOCS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
