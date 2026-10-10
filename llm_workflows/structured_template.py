import json
from typing import Any

from .llm import get_chat_model
from .schemas import BusinessPlanDetails

_COMMON = """
    Analyze the following business plan data and extract/structure the information according to the BusinessPlanDetails schema.
    Fill in as many fields as possible based on the provided data. If information is not available, leave fields as None or empty lists as appropriate.
"""

_STUDENT_STYLE = """    When giving feedback or structuring the data, always write in second person (use "you" instead of "they").
"""

_SCORING = """    The summary field should be in points or bullet format for clarity highlighting key aspects of the business plan.
    The scores should be on a 0-10 scale, where 0 is poor and 10 is excellent on various dimensions of the business plan.
"""


def build_structuring_prompt(json_data: Any, audience: str) -> str:
    """Build the structuring prompt. `audience` is "student" (second person) or "mentor" (neutral)."""
    if audience not in ("student", "mentor"):
        raise ValueError("audience must be 'student' or 'mentor'")
    style = _STUDENT_STYLE if audience == "student" else ""
    return f"""{_COMMON}{style}{_SCORING}
    Business Plan Data:
    {json.dumps(json_data, indent=2, ensure_ascii=False)}

    Please structure this data according to the BusinessPlanDetails schema.
    """


def _structure(json_data: Any, audience: str) -> BusinessPlanDetails:
    structured_llm = get_chat_model(temperature=0).with_structured_output(BusinessPlanDetails)
    return structured_llm.invoke(build_structuring_prompt(json_data, audience))


def get_structured_business_plan_student(json_data: Any) -> BusinessPlanDetails:
    return _structure(json_data, "student")


def get_structured_business_plan_mentor(json_data: Any) -> BusinessPlanDetails:
    return _structure(json_data, "mentor")
