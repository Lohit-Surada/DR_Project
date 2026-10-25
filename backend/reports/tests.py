import base64
import json
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import MedicalReport


ONE_PIXEL_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
    'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ReportApiTests(TestCase):
    def setUp(self):
        self.payload = {
            'classification': {'title': 'Moderate diabetic retinopathy', 'confidence': 92.4, 'severity': 'Moderate'},
            'lesions': {'summary': {'0': {'count': 1}}, 'total': 1},
            'gradcam': {'combined_path': ''},
        }

    def _image(self):
        return SimpleUploadedFile('fundus.png', ONE_PIXEL_PNG, content_type='image/png')

    @patch('reports.views._owner', return_value='user-a')
    def test_rejects_incomplete_analysis(self, owner):
        payload = {**self.payload, 'gradcam': {}}
        response = self.client.post('/api/reports/', {'image': self._image(), 'payload': json.dumps(payload)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MedicalReport.objects.count(), 0)

    @patch('reports.views._owner', return_value='user-a')
    def test_view_and_download_use_same_cached_pdf(self, owner):
        payload = {**self.payload, 'gradcam': {'combined_path': '/media/missing.png'}}
        create_response = self.client.post('/api/reports/', {'image': self._image(), 'payload': json.dumps(payload)})
        analysis_id = create_response.json()['analysis_id']

        view_response = self.client.get(f'/api/reports/{analysis_id}/view/')
        download_response = self.client.get(f'/api/reports/{analysis_id}/download/')

        self.assertEqual(view_response.status_code, 200)
        self.assertEqual(download_response.status_code, 200)
        self.assertIn('inline', view_response['Content-Disposition'])
        self.assertIn('attachment', download_response['Content-Disposition'])
        self.assertEqual(b''.join(view_response.streaming_content), b''.join(download_response.streaming_content))

    @patch('reports.views._owner', return_value='user-a')
    def test_report_with_expanded_user_profile(self, owner):
        payload = {
            **self.payload,
            'gradcam': {'combined_path': '/media/missing.png'},
            'metadata': {
                'report_date': 'October 18, 2026',
                'profile': {
                    'full_name': 'John Doe',
                    'age': '38',
                    'sex': 'Male',
                    'dob': '1988-08-20',
                    'email': 'johndoe@example.com',
                    'contact_no': '+19876543210',
                    'address': '456 Retinal Way, Vision City',
                    'blood_group': 'B+',
                },
            },
        }
        create_response = self.client.post('/api/reports/', {'image': self._image(), 'payload': json.dumps(payload)})
        self.assertEqual(create_response.status_code, 200)
        analysis_id = create_response.json()['analysis_id']

        view_response = self.client.get(f'/api/reports/{analysis_id}/view/')
        self.assertEqual(view_response.status_code, 200)
        pdf_bytes = b''.join(view_response.streaming_content)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))