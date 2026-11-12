"""Grade report generator - first draft.

Everything happens in one function and the grade cut-offs are hard-coded
in the middle of the loop.
"""

import csv
import sys


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_scores(row):
    scores = []
    for key in ("hw", "mid", "final"):
        raw = row.get(key, "")
        if raw == "":
            continue
        try:
            scores.append(float(raw))
        except ValueError:
            print("bad value: %s" % raw, file=sys.stderr)
    return scores


def process(path):
    rows = load_rows(path)
    report = []
    for row in rows:
        name = row["name"].strip()
        if not name:
            continue
        scores = parse_scores(row)
        if not scores:
            average = 0.0
        else:
            total = 0.0
            for score in scores:
                total += score
            average = total / len(scores)
        if average >= 90:
            grade = "A"
        elif average >= 80:
            grade = "B"
        elif average >= 70:
            grade = "C"
        elif average >= 60:
            grade = "D"
        else:
            grade = "F"
        report.append({"name": name, "average": average, "grade": grade})
    report.sort(key=lambda item: item["average"], reverse=True)
    print("name,average,grade")
    for item in report:
        print("%s,%.1f,%s" % (item["name"], item["average"], item["grade"]))
    return report


def main(path):
    process(path)


if __name__ == "__main__":
    main(sys.argv[1])
