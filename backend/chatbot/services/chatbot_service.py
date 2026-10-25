import re

from classifier.guidance_service import generate_guidance
from .domain_guard import REFUSAL
from .groq_service import generate_response


def detect_classification_in_query(message):
    """
    Detects if the user query is asking for recovery education/tips/medicines
    for a specific diabetic retinopathy classification level.
    """
    text = (message or '').strip().lower()
    if not text:
        return None

    # Check for recovery / treatment / advice intent
    has_advice_intent = bool(
        re.search(
            r'\b(recover|tip|tips|guidance|medic|drop|treat|suggest|recommend|diagnos|result|classif|what should i do|care|plan|action)\b',
            text,
        )
    )

    patterns = [
        (r'\b(no\s*dr|no\s*diabetic\s*retinopathy|normal\s*retina|no\s*retinopathy|stage\s*0)\b', 'No DR'),
        (r'\b(mild\s*npdr|mild\s*diabetic|mild\s*dr|stage\s*1)\b', 'Mild'),
        (r'\b(moderate\s*npdr|moderate\s*diabetic|moderate\s*dr|stage\s*2)\b', 'Moderate'),
        (r'\b(severe\s*npdr|severe\s*diabetic|severe\s*dr|stage\s*3)\b', 'Severe'),
        (r'\b(proliferative\s*diabetic|proliferative\s*dr|proliferative|pdr|stage\s*4)\b', 'Proliferative DR'),
    ]

    for pattern, severity_label in patterns:
        if re.search(pattern, text):
            if has_advice_intent or len(text.split()) <= 6:
                return severity_label

    return None


def answer(message, history=(), category='medical', classification=None):
    if category == 'blocked':
        return REFUSAL

    if classification:
        return str(generate_guidance(classification))

    detected = detect_classification_in_query(message)
    if detected:
        return str(generate_guidance(detected))

    return generate_response([*history, {'role': 'user', 'content': message}])