from evaluation import improvement_results, evaluation_summary

rows = improvement_results()
assert len(rows) == 5
assert [r['before'] for r in rows] == [65,80,85,30,100]
assert [r['after'] for r in rows] == [40,60,65,0,100]
assert all(r['pass'] for r in rows)
summary = evaluation_summary()
assert summary['ai_eval_judge']['correct_outputs_agreed'] == 4
assert summary['ai_eval_judge']['injected_failures_caught'] == 4
print('Evaluation evidence: 5/5 improvement cases PASS')
print('AI Eval Judge: 4/4 correct outputs agreed, 4/4 injected failures caught')
