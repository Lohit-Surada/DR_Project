import json
import logging
import time

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .classifier import ALLOWED_EXTENSIONS, classify_image
from .guidance_service import generate_guidance
from .gradcam_service import generate_visualization
from .lesion_service import generate_lesion_detection


LOGGER = logging.getLogger(__name__)


def add_cors_headers(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return response


@csrf_exempt
def classify(request):
    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}, status=204))
    if request.method != 'POST':
        return add_cors_headers(JsonResponse({'error': 'Use POST with an image file.'}, status=405))

    uploaded_file = request.FILES.get('image')
    if not uploaded_file:
        return add_cors_headers(JsonResponse({'error': 'Choose a retinal image before running the classification.'}, status=400))

    extension = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if extension not in ALLOWED_EXTENSIONS:
        return add_cors_headers(JsonResponse({'error': 'Use a JPG, JPEG, PNG, or WEBP image.'}, status=400))
    if uploaded_file.size > 12 * 1024 * 1024:
        return add_cors_headers(JsonResponse({'error': 'That image is larger than 12 MB. Choose a smaller file and try again.'}, status=413))

    try:
        result = classify_image(uploaded_file)
    except FileNotFoundError:
        LOGGER.exception('DR classification model is unavailable.')
        return add_cors_headers(JsonResponse({'error': 'The DR classification model is unavailable. Restore best_aptos_cnn.keras in the backend model folder.'}, status=503))
    except (OSError, ValueError):
        return add_cors_headers(JsonResponse({'error': 'That file could not be read as an image. Try another retinal photograph.'}, status=400))

    return add_cors_headers(JsonResponse(result))


@csrf_exempt
def guidance(request):
    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}, status=204))
    if request.method != 'POST':
        return add_cors_headers(JsonResponse({'error': 'Use POST with classification data.'}, status=405))

    try:
        payload = request.body.decode('utf-8') or '{}'
        classification = json.loads(payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return add_cors_headers(JsonResponse({'error': 'The classification data is invalid.'}, status=400))

    try:
        result = generate_guidance(classification)
    except Exception:
        LOGGER.exception('Personalized guidance generation failed.')
        return add_cors_headers(JsonResponse({'error': 'Educational guidance is temporarily unavailable.'}, status=503))

    return add_cors_headers(JsonResponse({'success': True, **result}))


@csrf_exempt
def gradcam(request):
    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}, status=204))
    if request.method != 'POST':
        return add_cors_headers(JsonResponse({'error': 'Use POST with an image file.'}, status=405))

    uploaded_file = request.FILES.get('image')
    if not uploaded_file:
        return add_cors_headers(JsonResponse({'error': 'No image was uploaded.'}, status=400))

    extension = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if extension not in ALLOWED_EXTENSIONS:
        return add_cors_headers(JsonResponse({'error': 'Use a JPG, JPEG, PNG, or WEBP image.'}, status=400))
    if uploaded_file.content_type not in {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}:
        return add_cors_headers(JsonResponse({'error': 'The uploaded file is not a supported image.'}, status=400))
    if uploaded_file.size > 12 * 1024 * 1024:
        return add_cors_headers(JsonResponse({'error': 'That image is larger than 12 MB.'}, status=413))

    started_at = time.perf_counter()
    try:
        result = generate_visualization(uploaded_file, settings.MEDIA_ROOT)
    except (ValueError, OSError, FileNotFoundError) as error:
        LOGGER.exception('Grad-CAM input or model error: %s', error)
        return add_cors_headers(JsonResponse({'error': 'That file could not be processed as a retinal image.'}, status=400))
    except Exception:
        LOGGER.exception('Grad-CAM generation failed.')
        return add_cors_headers(JsonResponse({'error': 'Grad-CAM generation failed.'}, status=500))

    output_urls = {
        key: f'{settings.MEDIA_URL}{path}'
        for key, path in result.pop('files').items()
    }
    result.update({
        'success': True,
        'message': 'Grad-CAM visualization generated successfully',
        'results': output_urls,
        'processing_time': round(time.perf_counter() - started_at, 3),
    })
    return add_cors_headers(JsonResponse(result))


@csrf_exempt
def lesions(request):
    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}, status=204))
    if request.method != 'POST':
        return add_cors_headers(JsonResponse({'error': 'Use POST with an image file.'}, status=405))

    uploaded_file = request.FILES.get('image')
    if not uploaded_file:
        return add_cors_headers(JsonResponse({'error': 'No image was uploaded.'}, status=400))

    extension = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if extension not in ALLOWED_EXTENSIONS:
        return add_cors_headers(JsonResponse({'error': 'Use a JPG, JPEG, PNG, or WEBP image.'}, status=400))
    if uploaded_file.content_type not in {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}:
        return add_cors_headers(JsonResponse({'error': 'The uploaded file is not a supported image.'}, status=400))
    if uploaded_file.size > 12 * 1024 * 1024:
        return add_cors_headers(JsonResponse({'error': 'That image is larger than 12 MB.'}, status=413))

    try:
        result = generate_lesion_detection(uploaded_file, settings.MEDIA_ROOT)
    except ValueError as error:
        return add_cors_headers(JsonResponse({'error': str(error)}, status=400))
    except Exception:
        LOGGER.exception('Lesion detection failed.')
        return add_cors_headers(JsonResponse({'error': 'Lesion detection could not be completed.'}, status=500))

    result['original_url'] = f"{settings.MEDIA_URL}{result['original_url']}"
    result['image_url'] = f"{settings.MEDIA_URL}{result['image_url']}"
    result['download_url'] = f"{settings.MEDIA_URL}{result['download_url']}"
    return add_cors_headers(JsonResponse({'success': True, 'result': result}))