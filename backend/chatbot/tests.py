from unittest.mock import MagicMock, patch
import json
import re

from django.test import SimpleTestCase, TestCase, override_settings

from .services.chatbot_service import answer
from .services.domain_guard import classify_topic
from classifier.guidance_service import (
    NO_DR_MESSAGE,
    generate_guidance,
    normalize_classification,
    parse_response_to_components,
)


class DomainGuardTests(SimpleTestCase):
    def test_allows_retinal_and_website_questions(self):
        allowed = [
            'What is diabetic retinopathy?',
            'What are microaneurysms?',
            'What is a hard exudate?',
            'What does Grad-CAM mean?',
            'How does lesion detection work?',
            'How do I upload an image?',
            'How can I download the report?',
        ]
        for message in allowed:
            with self.subTest(message=message):
                self.assertNotEqual(classify_topic(message), 'blocked')

    def test_blocks_unrelated_questions(self):
        blocked = [
            'What is Instagram?',
            'Tell me a joke.',
            'Who won the cricket match?',
            'Write a Python program.',
            'What is Bitcoin?',
            'Give me a recipe.',
            'Tell me about politics.',
        ]
        for message in blocked:
            with self.subTest(message=message):
                self.assertEqual(classify_topic(message), 'blocked')

    def test_uses_conversation_context(self):
        self.assertNotEqual(
            classify_topic('What are its stages?', ['Diabetic retinopathy is a disease of the retina.']),
            'blocked',
        )

    def test_mixed_intent_is_evaluated_by_context(self):
        self.assertNotEqual(
            classify_topic('What is diabetic retinopathy and can I post about it on Instagram?'),
            'blocked',
        )


class RecoveryGuidanceLogicTests(TestCase):
    SUPPORTED_SEVERITIES = [
        'Mild',
        'Moderate',
        'Severe',
        'Proliferative DR',
    ]

    def test_no_dr_exact_output_and_no_medicines(self):
        test_inputs = [
            'No DR',
            'No diabetic retinopathy',
            {'label': 'No DR', 'title': 'No diabetic retinopathy', 'severity': 'No DR'},
            {'severity': '0'},
        ]
        expected_text = (
            'No diabetic retinopathy detected by the AI model. '
            'No DR-specific suggestions are required based on this result. '
            'Continue routine eye examinations as advised by your eye-care professional.'
        )
        for input_data in test_inputs:
            with self.subTest(input_data=input_data):
                result = generate_guidance(input_data)
                self.assertEqual(str(result), expected_text)
                self.assertEqual(result['response'], expected_text)
                self.assertEqual(result['tips'], [])
                self.assertEqual(result['medications'], [])
                self.assertNotIn('**Medicines:**', str(result))

    def _assert_required_format(self, text):
        self.assertIn('**Recovery Tips:**', text)
        self.assertIn('**Medicines:**', text)

        tips_match = re.search(r'\*\*Recovery Tips:\*\*\s*(.*?)(?=\*\*Medicines:\*\*)', text, re.DOTALL)
        self.assertIsNotNone(tips_match, 'Recovery Tips block missing')
        tips_lines = [line.strip() for line in tips_match.group(1).splitlines() if re.match(r'^\d+\.\s*', line.strip())]
        self.assertEqual(len(tips_lines), 3, f'Expected exactly 3 recovery tips, got {len(tips_lines)}')

        for tip in tips_lines:
            line_count = len(tip.splitlines())
            self.assertTrue(1 <= line_count <= 2, f'Tip exceeds 2 lines: {tip}')

        meds_match = re.search(r'\*\*Medicines:\*\*\s*(.*?)$', text, re.DOTALL)
        self.assertIsNotNone(meds_match, 'Medicines block missing')
        meds_lines = [line.strip() for line in meds_match.group(1).splitlines() if line.strip().startswith(('-', '*'))]
        self.assertEqual(len(meds_lines), 3, f'Expected exactly 3 medicine bullets, got {len(meds_lines)}')

    def _assert_medical_safety(self, text, medications):
        forbidden = re.compile(
            r'\b(anti-vegf|aflibercept|bevacizumab|ranibizumab|brolucizumab|faricimab|injection|intravitreal)\b',
            re.IGNORECASE,
        )
        self.assertIsNone(forbidden.search(text), f'Forbidden injection term found in text: {text}')
        for med in medications:
            self.assertIsNone(forbidden.search(med.get('name', '')), f'Forbidden term in med name: {med}')
            self.assertIsNone(forbidden.search(med.get('category', '')), f'Forbidden term in med category: {med}')

        # Accept any phrase indicating eye drops don't reverse/treat DR
        eye_drop_disclaimer = re.compile(
            r'(no routine eye drop (treats|reverses|replaces)|'
            r'no.*eye drop.*reverse|'
            r'eye drop.*does not (reverse|treat)|'
            r'cannot (treat|reverse|halt)|'
            r'no routine eye drop)',
            re.IGNORECASE,
        )
        self.assertTrue(
            eye_drop_disclaimer.search(text),
            'Eye drop disclaimer (no routine eye drop treats/reverses/replaces DR) missing from medicines section',
        )
        self.assertTrue(
            re.search(r'urgent|emergency|immediate', text, re.IGNORECASE),
            'Emergency/urgent warning for sudden vision loss/pain missing',
        )
        self.assertNotIn('I prescribe', text)
        self.assertNotIn('take 2 tablets', text)

    @override_settings(GROQ_API_KEY='')
    def test_supported_severity_levels_format_and_safety(self):
        """Tests the curated response content for all supported DR severity levels.
        Groq is intentionally disabled so that the deterministic curated responses are tested,
        not a live API call whose phrasing we cannot control.
        """
        for severity in self.SUPPORTED_SEVERITIES:
            with self.subTest(severity=severity):
                result = generate_guidance(severity)
                response_text = str(result)
                self._assert_required_format(response_text)
                self._assert_medical_safety(response_text, result['medications'])
                self.assertEqual(len(result['tips']), 3)
                self.assertEqual(len(result['medications']), 3)


    def test_invalid_classification_handled_gracefully(self):
        invalid_cases = [None, '', {}, {'other': 'value'}, 'UnrecognizedDR']
        for case in invalid_cases:
            with self.subTest(case=case):
                result = generate_guidance(case)
                self.assertIsNotNone(result)
                self.assertIn('**Recovery Tips:**', str(result))
                self.assertIn('**Medicines:**', str(result))
                self.assertEqual(len(result['tips']), 3)
                self.assertEqual(len(result['medications']), 3)

    @patch('classifier.guidance_service.settings')
    def test_empty_groq_response_falls_back_gracefully(self, mock_settings):
        mock_settings.GROQ_API_KEY = 'test-key'
        mock_settings.GROQ_MODEL = 'llama-3.3-70b-versatile'

        mock_groq_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = []
        mock_groq_client.chat.completions.create.return_value = mock_completion

        with patch.dict('sys.modules', {'groq': MagicMock(Groq=MagicMock(return_value=mock_groq_client))}):
            result = generate_guidance('Moderate')
            self._assert_required_format(str(result))
            self.assertEqual(len(result['tips']), 3)

    @patch('classifier.guidance_service.settings')
    def test_forbidden_injection_term_rejected_and_fallback_used(self, mock_settings):
        mock_settings.GROQ_API_KEY = 'test-key'
        mock_settings.GROQ_MODEL = 'llama-3.3-70b-versatile'

        mock_groq_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = (
            '**Recovery Tips:**\n'
            '1. Arrange follow up.\n'
            '2. Control sugar.\n'
            '3. Seek urgent care.\n\n'
            '**Medicines:**\n'
            '- Anti-VEGF injection (aflibercept): Recommended for retinal swelling.\n'
            '- Ranibizumab: Second injection option.\n'
            '- Eye drop: General drop.'
        )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_groq_client.chat.completions.create.return_value = mock_completion

        with patch.dict('sys.modules', {'groq': MagicMock(Groq=MagicMock(return_value=mock_groq_client))}):
            result = generate_guidance('Severe')
            response_text = str(result)
            self._assert_required_format(response_text)
            self._assert_medical_safety(response_text, result['medications'])
            self.assertNotIn('aflibercept', response_text.lower())
            self.assertNotIn('anti-vegf', response_text.lower())

    def test_guidance_api_endpoint(self):
        payload = {'label': 'Moderate', 'genuine_confidence': 92.4}
        response = self.client.post('/api/guidance/', json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data.get('tips', [])), 3)
        self.assertEqual(len(data.get('medications', [])), 3)
        self.assertIn('**Recovery Tips:**', data.get('response', ''))

    def test_chat_endpoint_with_classification_payload(self):
        payload = {'classification': 'Mild'}
        response = self.client.post('/api/chat/', json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('**Recovery Tips:**', data.get('response', ''))
        self.assertIn('**Medicines:**', data.get('response', ''))

    def test_chat_endpoint_with_no_dr(self):
        payload = {'message': 'What are the recovery tips for No DR?'}
        response = self.client.post('/api/chat/', json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        # The No DR response must contain the standard message text (not a REFUSAL or DR tips)
        response_text = data.get('response', '')
        self.assertIn('No diabetic retinopathy detected by the AI model', response_text)
        self.assertIn('Continue routine eye examinations', response_text)
        self.assertNotIn('**Recovery Tips:**', response_text)
        self.assertNotIn('**Medicines:**', response_text)
