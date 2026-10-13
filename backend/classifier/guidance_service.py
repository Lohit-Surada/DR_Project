import json

from django.conf import settings


MEDICATION_REFERENCE = [
    {'name': 'Aflibercept', 'category': 'Anti-VEGF injection'},
    {'name': 'Bevacizumab', 'category': 'Anti-VEGF injection'},
    {'name': 'Ranibizumab', 'category': 'Anti-VEGF injection'},
]

FALLBACK_TIPS = [
    'Arrange an appointment with an eye-care professional to review this AI-assisted result and discuss an appropriate follow-up schedule.',
    'Keep diabetes, blood pressure, and cholesterol monitoring aligned with your healthcare team\'s plan; do not change medicines based on this result.',
    'Seek urgent eye care for sudden vision loss, a rapid increase in floaters or flashes, or severe eye pain.',
]


def generate_guidance(classification):
    from groq import Groq

    if not settings.GROQ_API_KEY:
        raise RuntimeError('Guidance provider is not configured.')

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                'role': 'system',
                'content': (
                    'You provide concise educational diabetic-retinopathy care guidance. '
                    'Never diagnose, prescribe, recommend a medicine, or promise recovery. '
                    'Return valid JSON only with exactly three strings in a "tips" array. '
                    'Each tip must be 1 or 2 short lines and a practical next step involving professional follow-up, '
                    'safe diabetes/vision monitoring, or urgent warning signs. '
                    'Tailor urgency to the DR severity in the classification. Mention that the uploaded AI result is not a diagnosis.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps({
                    'classification': classification,
                    'request': 'Give the three most important educational management and prevention priorities for this DR level. Do not promise a cure or prescribe treatment.',
                }),
            },
        ],
        temperature=0.1,
        max_tokens=450,
    )
    content = response.choices[0].message.content.strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find('{'), content.rfind('}')
        if start < 0 or end <= start:
            return {'tips': FALLBACK_TIPS, 'medications': MEDICATION_REFERENCE}
        try:
            payload = json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return {'tips': FALLBACK_TIPS, 'medications': MEDICATION_REFERENCE}

    tips = payload.get('tips')
    if not isinstance(tips, list) or len(tips) != 3 or not all(isinstance(tip, str) and tip.strip() for tip in tips):
        return {'tips': FALLBACK_TIPS, 'medications': MEDICATION_REFERENCE}
    return {'tips': [tip.strip() for tip in tips], 'medications': MEDICATION_REFERENCE}