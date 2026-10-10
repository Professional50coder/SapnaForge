"""Validate a structured plan against the BusinessPlanDetails schema and report coverage.

Runs offline (no API keys). The bundled sample_plan.json is the structured
output of a handwritten Odia business plan (a metal-fabrication shop), taken
from the repo's own translation demo. It is not a fresh model run.

    python examples/inspect_plan.py [path/to/plan.json]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_workflows.schemas import BusinessPlanDetails  # noqa: E402
from llm_workflows.text_utils import section_coverage  # noqa: E402

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("sample_plan.json")
plan = BusinessPlanDetails(**json.loads(path.read_text(encoding="utf-8")))
cov = section_coverage(plan)

print(f"Plan: {plan.title}  (language: {plan.language})")
print(f"Sections filled: {cov['filled_count']}/{cov['total']}")
for name in cov["filled"]:
    print(f"  [x] {name}")
for name in cov["missing"]:
    print(f"  [ ] {name}  <- ask the founder")
print(f"Mean section score: {cov['mean_score'] if cov['mean_score'] is not None else 'n/a (plan has no scores yet)'}")
