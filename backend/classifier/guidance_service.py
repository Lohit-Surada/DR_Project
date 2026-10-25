import json
import logging
import re

from django.conf import settings

LOGGER = logging.getLogger(__name__)

# Non-injectable educational references for clinician discussion. Injections (including anti-VEGF) are excluded.
# Named medicine references — educational, for clinician discussion only. No injections.
MEDICATION_REFERENCE = [
    {
        'name': 'Systane Ultra / Refresh Optive (Preservative-free)',
        'category': 'Lubricating eye drops for dry eye comfort; no routine eye drop treats or reverses DR',
    },
    {
        'name': 'Fenofibrate (Lipanthyl / Tricor)',
        'category': 'Lipid-regulating agent with ACCORD-Eye trial evidence for slowing DR progression (physician prescribed)',
    },
    {
        'name': 'Metformin (Glucophage)',
        'category': 'First-line oral diabetes medication supporting long-term glycaemic control to protect retinal microvasculature',
    },
]

NO_DR_MESSAGE = (
    'No diabetic retinopathy detected by the AI model. '
    'No DR-specific suggestions are required based on this result. '
    'Continue routine eye examinations as advised by your eye-care professional.'
)

CURATED_RESPONSES = {
    'mild': (
        '**Recovery Tips:**\n'
        '1. Schedule a comprehensive dilated retinal examination with an eye-care professional every 6–12 months to monitor microvascular changes.\n'
        '2. Maintain steady, optimal blood glucose (HbA1c) and blood pressure levels in coordination with your primary physician to slow disease progression.\n'
        '3. Stay alert for sudden vision changes and seek urgent ophthalmic evaluation immediately if you notice sudden vision loss, new flashes, or floaters.\n\n'
        '**Medicines:**\n'
        '- Systane Ultra / Refresh Optive (preservative-free artificial tears): Lubricating drops for dry eye comfort common in diabetes; no routine eye drop treats or reverses diabetic retinopathy — for surface relief only.\n'
        '- Fenofibrate (e.g., Lipanthyl / Tricor): A lipid-regulating agent with evidence from the ACCORD-Eye study for slowing early DR progression; must be prescribed and monitored by your physician.\n'
        '- Metformin (e.g., Glucophage): The first-line oral diabetes medication for long-term blood glucose control that protects retinal capillaries; any adjustment must be made under your prescribing physician\'s guidance.'
    ),
    'moderate': (
        '**Recovery Tips:**\n'
        '1. Arrange a specialist follow-up examination with an ophthalmologist or retina specialist within 3–6 months for close retinal evaluation.\n'
        '2. Work closely with your healthcare team to tightly regulate blood glucose, blood pressure, and cholesterol targets, preventing further capillary leakage.\n'
        '3. Monitor your visual field daily and seek urgent emergency eye care immediately if you experience sudden blurry vision, curtains across your sight, or severe eye pain.\n\n'
        '**Medicines:**\n'
        '- Refresh Plus / Blink Tears (preservative-free): Lubricating drops for dry eye surface comfort; no routine eye drop treats or reverses diabetic retinal vascular damage.\n'
        '- Fenofibrate (e.g., Lipanthyl / Tricor): Clinical trials show this oral lipid-lowering agent may slow moderate NPDR progression; discuss with your ophthalmologist and prescribing physician before use.\n'
        '- Lisinopril / Ramipril (ACE inhibitors, e.g., Zestril / Altace): Blood pressure medications with evidence of retinal and renal microvasculature protection; discuss with your cardiologist or internist for appropriate prescription.'
    ),
    'severe': (
        '**Recovery Tips:**\n'
        '1. Consult an ophthalmologist or retina specialist promptly (recommended within 2–4 weeks) for comprehensive diagnostic staging and specialized surveillance.\n'
        '2. Partner with your diabetes management team to stabilize blood sugar and blood pressure without rapid unmonitored fluctuations that could stress fragile vessels.\n'
        '3. Treat any sudden vision changes as a medical emergency—seek urgent ophthalmic assessment immediately for vision loss, flashes, floaters, or eye pain.\n\n'
        '**Medicines:**\n'
        '- Systane Ultra (preservative-free artificial tears): Safe topical lubricant for ocular surface comfort; no routine eye drop treats or reverses retinal ischemia or diabetic retinopathy.\n'
        '- Fenofibrate (e.g., Lipanthyl / Tricor): Discuss with your retina specialist and prescribing physician; clinical evidence supports a role in reducing retinal microvascular complications in severe NPDR.\n'
        '- Empagliflozin / Dapagliflozin (e.g., Jardiance / Farxiga — SGLT2 inhibitors): Oral diabetes agents with proven cardiovascular-renal protective benefits; discuss suitability and safety with your physician for systemic DR risk reduction.'
    ),
    'proliferative': (
        '**Recovery Tips:**\n'
        '1. Seek urgent specialist consultation with a retina specialist or ophthalmologist for comprehensive assessment, as proliferative changes carry a high risk of severe vision loss.\n'
        '2. Coordinate closely with your medical team to maintain strict blood glucose and blood pressure control to protect remaining retinal vasculature.\n'
        '3. Go to an emergency eye care center immediately if you notice sudden vision loss, a shower of dark floaters, bright flashes, or severe eye pain.\n\n'
        '**Medicines:**\n'
        '- Refresh Optive Advanced (preservative-free): Lubricating drops for ocular surface comfort; no routine eye drop treats or halts abnormal retinal neovascularization.\n'
        '- Fenofibrate (e.g., Lipanthyl / Tricor): Discuss with your retina specialist; clinical evidence supports its use in reducing DR severity and slowing progression of retinal microvascular disease.\n'
        '- Lisinopril / Ramipril (ACE inhibitor) or Empagliflozin (e.g., Jardiance): Discuss with your prescribing physician for comprehensive cardiovascular-metabolic risk management to protect remaining retinal vasculature; never adjust on your own.'
    ),
}

INVALID_FALLBACK_RESPONSE = (
    '**Recovery Tips:**\n'
    '1. Obtain a validated diabetic retinopathy classification from a clinical fundus examination or the AI analysis before proceeding with targeted guidance.\n'
    '2. Continue regular comprehensive dilated eye examinations with an eye-care professional to monitor retinal health.\n'
    '3. Seek urgent medical assessment immediately if you experience sudden vision loss, new flashes or floaters, or severe eye pain.\n\n'
    '**Medicines:**\n'
    '- Systane Ultra / Refresh Optive (preservative-free artificial tears): Ocular surface lubricant for dry eye comfort; no routine eye drop treats or reverses diabetic retinopathy.\n'
    '- Fenofibrate (e.g., Lipanthyl / Tricor): A lipid-regulating agent discussed in DR management; review with your prescribing physician whether this is appropriate for your profile.\n'
    '- Metformin (e.g., Glucophage) or ACE inhibitor (e.g., Lisinopril / Ramipril): Discuss individualized blood glucose and blood pressure targets and medications with your physician to protect retinal microvasculature.'
)

FORBIDDEN_TERMS = re.compile(
    r'\b(anti-vegf|aflibercept|bevacizumab|ranibizumab|brolucizumab|faricimab|injection|intravitreal)\b',
    re.IGNORECASE,
)


class GuidanceResponse(dict):
    """
    Dictionary maintaining full backwards-compatibility with existing frontend
    and report services (keys: 'tips', 'medications', 'response') while
    stringifying directly to the formatted response text.
    """

    def __init__(self, tips=None, medications=None, response='', severity=None, **kwargs):
        super().__init__(
            tips=tips if tips is not None else [],
            medications=medications if medications is not None else [],
            response=response,
            severity=severity,
            **kwargs,
        )

    def __str__(self):
        return self.get('response', '')


def normalize_classification(classification):
    """
    Normalizes arbitrary classification inputs (dict, string, int) into standard severity metadata.
    Returns: (severity_key, display_title, confidence, patient_info)
    """
    if classification is None:
        return None, None, None, {}

    raw_text = ''
    confidence = None
    patient_info = {}

    if isinstance(classification, dict):
        raw_text = str(
            classification.get('severity')
            or classification.get('label')
            or classification.get('title')
            or classification.get('name')
            or classification.get('prediction')
            or classification.get('class')
            or ''
        ).strip()
        confidence = (
            classification.get('genuine_confidence')
            or classification.get('actual_confidence')
            or classification.get('model_confidence')
            or classification.get('confidence')
        )
        patient_info = (
            classification.get('patient')
            or classification.get('profile')
            or classification.get('patient_info')
            or {}
        )
    elif isinstance(classification, (str, int, float)):
        raw_text = str(classification).strip()

    normalized = raw_text.lower()

    if re.search(r'\b(no\s*dr|no\s*diabetic|normal|stage\s*0|grade\s*0|^0$|none)\b', normalized):
        return 'no_dr', 'No diabetic retinopathy', confidence, patient_info
    if re.search(r'\b(mild\s*npdr|mild\s*diabetic|mild|stage\s*1|grade\s*1|^1$)\b', normalized):
        return 'mild', 'Mild diabetic retinopathy', confidence, patient_info
    if re.search(r'\b(moderate\s*npdr|moderate\s*diabetic|moderate|stage\s*2|grade\s*2|^2$)\b', normalized):
        return 'moderate', 'Moderate diabetic retinopathy', confidence, patient_info
    if re.search(r'\b(severe\s*npdr|severe\s*diabetic|severe|stage\s*3|grade\s*3|^3$)\b', normalized):
        return 'severe', 'Severe diabetic retinopathy', confidence, patient_info
    if re.search(r'\b(proliferative|pdr|stage\s*4|grade\s*4|^4$)\b', normalized):
        return 'proliferative', 'Proliferative diabetic retinopathy', confidence, patient_info

    return None, raw_text or None, confidence, patient_info


def parse_response_to_components(text):
    """
    Parses a response formatted with **Recovery Tips:** and **Medicines:**
    into list of tips and list of medication dictionaries.
    """
    tips = []
    medications = []

    tips_match = re.search(r'\*\*Recovery Tips:\*\*\s*(.*?)(?=\*\*Medicines:\*\*|$)', text, re.DOTALL | re.IGNORECASE)
    if tips_match:
        tips_block = tips_match.group(1).strip()
        for line in tips_block.splitlines():
            line = line.strip()
            if re.match(r'^\d+\.\s*', line):
                clean_tip = re.sub(r'^\d+\.\s*', '', line).strip()
                if clean_tip:
                    tips.append(clean_tip)

    meds_match = re.search(r'\*\*Medicines:\*\*\s*(.*?)$', text, re.DOTALL | re.IGNORECASE)
    if meds_match:
        meds_block = meds_match.group(1).strip()
        for line in meds_block.splitlines():
            line = line.strip()
            if line.startswith(('-', '*')):
                clean_med = line.lstrip('-* ').strip()
                if not clean_med:
                    continue
                if ':' in clean_med:
                    name, category = clean_med.split(':', 1)
                elif ' - ' in clean_med:
                    name, category = clean_med.split(' - ', 1)
                else:
                    name, category = clean_med, 'Clinician discussion reference'
                name = name.replace('**', '').strip()
                category = category.replace('**', '').strip()
                medications.append({'name': name, 'category': category})

    return tips[:3], medications[:3]


def generate_guidance(classification):
    """
    Generates educational recovery and eye-care guidance based on DR classification.
    Returns GuidanceResponse dict with 'tips', 'medications', 'response', and 'severity'.
    """
    severity_key, display_title, confidence, patient_info = normalize_classification(classification)

    # 1. No DR: Display exact message, do not recommend medicines
    if severity_key == 'no_dr':
        return GuidanceResponse(
            tips=[],
            medications=[],
            response=NO_DR_MESSAGE,
            severity='No DR',
        )

    # 2. Invalid or unrecognized classification
    if severity_key is None:
        LOGGER.warning('Invalid DR classification received: %s', classification)
        fallback_text = INVALID_FALLBACK_RESPONSE
        tips, meds = parse_response_to_components(fallback_text)
        return GuidanceResponse(
            tips=tips,
            medications=meds or MEDICATION_REFERENCE,
            response=fallback_text,
            severity='Unknown',
        )

    # 3. Mild, Moderate, Severe, or Proliferative DR
    default_text = CURATED_RESPONSES[severity_key]
    default_tips, default_meds = parse_response_to_components(default_text)

    # If Groq is not configured, return safe curated response directly
    if not getattr(settings, 'GROQ_API_KEY', ''):
        LOGGER.info('Groq API key not configured; using curated response for %s', severity_key)
        return GuidanceResponse(
            tips=default_tips,
            medications=default_meds,
            response=default_text,
            severity=display_title,
        )

    try:
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
        system_prompt = (
            'You are a specialized diabetic retinopathy educational care assistant for an AI-assisted analysis platform.\n'
            'Generate evidence-based educational recovery guidance and eye-care tips strictly tailored to the predicted classification.\n'
            'Make the explanation informative and specialist-like, but never claim to be a qualified ophthalmologist.\n\n'
            'CRITICAL SAFETY AND CLINICAL RULES:\n'
            '1. Use the actual classification result and available patient info. Never invent medical history, symptoms, test results, or diagnoses.\n'
            '2. Do not prescribe medicines, dosages, frequencies, or treatment courses based solely on the AI classification.\n'
            '3. NEVER recommend injections, including anti-VEGF injections (e.g., aflibercept, bevacizumab, ranibizumab). Focus only on non-injectable options and clinician discussion topics.\n'
            '4. Do not automatically recommend eye drops or drugs to treat DR. Explain that no routine eye drop reverses diabetic retinal damage; any medicine must be selected by a qualified clinician for a specific indication.\n'
            '5. If no specific medicine is appropriate, list three relevant medicine-related discussion topics or state that no DR-specific medicine can safely be recommended from the AI result alone. Never invent three drug recommendations merely to fill the format.\n'
            '6. Do not suggest unproven cures, supplements, or self-medication. Emphasize appropriate ophthalmology review and blood glucose, blood pressure, and cholesterol management as relevant.\n'
            '7. For sudden vision loss, new flashes or a sudden increase in floaters, or severe eye pain, advise urgent medical assessment.\n\n'
            'REQUIRED RESPONSE FORMAT (STRICT):\n'
            '**Recovery Tips:**\n'
            '1. [Practical, classification-appropriate eye-care or follow-up advice in 1–2 lines.]\n'
            '2. [A second important recommendation in 1–2 lines.]\n'
            '3. [A third important recommendation in 1–2 lines.]\n\n'
            '**Medicines:**\n'
            '- [Medicine or eye-drop name, if clinically appropriate, with its general purpose.]\n'
            '- [Second option, if clinically appropriate.]\n'
            '- [Third option, if clinically appropriate.]'
        )

        user_content = json.dumps({
            'classification': display_title,
            'confidence': f'{confidence}%' if confidence is not None else 'Not specified',
            'patient_information': patient_info if patient_info else 'Not provided',
            'request': (
                f'Provide the 3 recovery tips and 3 non-injectable medicine or clinician discussion points '
                f'for confirmed classification: {display_title}.'
            ),
        })

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip() if response.choices else ''
        if not content:
            raise ValueError('Groq returned an empty response.')

        # Reject responses containing forbidden injection terms
        if FORBIDDEN_TERMS.search(content):
            LOGGER.warning('Groq response contained forbidden injection references; falling back to curated response.')
            return GuidanceResponse(
                tips=default_tips,
                medications=default_meds,
                response=default_text,
                severity=display_title,
            )

        tips, meds = parse_response_to_components(content)
        if len(tips) != 3 or len(meds) != 3:
            LOGGER.warning('Groq response failed structural validation (%d tips, %d meds); using curated fallback.', len(tips), len(meds))
            return GuidanceResponse(
                tips=default_tips,
                medications=default_meds,
                response=default_text,
                severity=display_title,
            )

        return GuidanceResponse(
            tips=tips,
            medications=meds,
            response=content,
            severity=display_title,
        )

    except Exception as exc:
        LOGGER.exception('Groq guidance generation failed: %s; using curated response.', exc)
        return GuidanceResponse(
            tips=default_tips,
            medications=default_meds,
            response=default_text,
            severity=display_title,
        )