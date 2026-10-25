import re


REFUSAL = "I'm designed to help with diabetic retinopathy, related medical and eye-health topics, and questions about this website. I can't help with unrelated topics."
ALLOWED_TERMS = {'diabet', 'retin', 'fundus', 'macula', 'ophthalm', 'eye', 'vision', 'blind', 'blur', 'microaneurysm', 'haemorrhage', 'hemorrhage', 'exudate', 'lesion', 'grad-cam', 'gradcam', 'yolo', 'heatmap', 'classification', 'confidence', 'upload', 'website', 'dashboard', 'report', 'profile', 'login', 'register', 'image', 'retinal', 'cornea', 'glaucoma'}
BLOCKED_INTENTS = re.compile(r'\b(politic|president|cricket|recipe|bitcoin|instagram|youtube|facebook|joke|romantic|pollution|capital of|mathematics|coding interview)\b', re.I)
MEDICAL_CONTEXT = re.compile(r'\b(diabet|eye|vision|retin|doctor|symptom|disease|health|medical|pain|blind|flash|float|cornea)\b', re.I)


def classify_topic(message, history=()):
    text = message.strip().lower()
    if not text:
        return 'blocked'
    has_dr_abbreviation = bool(re.search(r'\b(dr|npdr|pdr)\b', text))
    has_allowed = any(term in text for term in ALLOWED_TERMS) or has_dr_abbreviation
    has_medical_context = bool(MEDICAL_CONTEXT.search(text))
    has_blocked_intent = bool(BLOCKED_INTENTS.search(text))
    if has_blocked_intent and not has_medical_context and not has_allowed:
        return 'blocked'
    if has_allowed or has_medical_context:
        website_terms = ('website', 'upload', 'dashboard', 'report', 'profile', 'login', 'register')
        return 'website' if any(term in text for term in website_terms) else 'medical'
    previous = ' '.join(history).lower()
    if previous and (any(term in previous for term in ALLOWED_TERMS) or MEDICAL_CONTEXT.search(previous)):
        return 'medical'
    return 'blocked'