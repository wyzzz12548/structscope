"""Grade report generator - refactored.

The grade scale is data, the report is built in one place, and printing is
a separate concern.
"""

import csv
import sys
from statistics import mean

GRADE_CUTOFFS = ((90, "A"), (80, "B"), (70, "C"), (60, "D"))


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_scores(row):
    scores = []
    for key in ("hw", "mid", "final"):
        raw = (row.get(key) or "").strip()
        if not raw:
            continue
        try:
            scores.append(float(raw))
        except ValueError:
            print(f"bad value for {row.get('name')}: {raw}", file=sys.stderr)
    return scores


def letter_grade(average):
    for cutoff, letter in GRADE_CUTOFFS:
        if average >= cutoff:
            return letter
    return "F"


def build_report(rows):
    report = []
    for row in rows:
        name = row["name"].strip()
        if not name:
            continue
        scores = parse_scores(row)
        average = mean(scores) if scores else 0.0
        report.append({"name": name, "average": average, "grade": letter_grade(average)})
    report.sort(key=lambda item: item["average"], reverse=True)
    return report


def format_csv(report):
    lines = ["name,average,grade"]
    for item in report:
        lines.append(f"{item['name']},{item['average']:.1f},{item['grade']}")
    return "\n".join(lines)


def main(path):
    print(format_csv(build_report(load_rows(path))))


if __name__ == "__main__":
    main(sys.argv[1])
