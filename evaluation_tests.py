from evaluation import improvement_results, evaluation_summary

rows = improvement_results()
assert len(rows) == 5
assert [r["before"] for r in rows] == [65, 80, 85, 30, 100]
assert [r["after"] for r in rows] == [40, 60, 65, 0, 100]
assert all(r["pass"] for r in rows)
summary = evaluation_summary()
assert summary["improvement_passed"] == 5
assert summary["improvement_total"] == 5
print("Evaluation evidence: 5/5 same-case improvement checks PASS")
