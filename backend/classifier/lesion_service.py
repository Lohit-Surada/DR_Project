from pathlib import Path
from threading import RLock
import uuid

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import torch

from .gradcam_service import CLASS_NAMES, MODEL_LOCK, get_model


CLASS_INFO = {
    0: {'name': CLASS_NAMES[0], 'short': 'MA', 'color': (255, 0, 0)},
    1: {'name': CLASS_NAMES[1], 'short': 'HE', 'color': (0, 0, 255)},
    2: {'name': CLASS_NAMES[2], 'short': 'EX', 'color': (0, 255, 0)},
    3: {'name': CLASS_NAMES[3], 'short': 'SE', 'color': (255, 255, 0)},
}


def _draw_annotations(image, prediction):
    annotated = image.copy().convert('RGB')
    draw = ImageDraw.Draw(annotated)
    for box in prediction.boxes:
        class_id = int(box.cls[0].item())
        if class_id in CLASS_INFO:
            coordinates = [round(value) for value in box.xyxy[0].tolist()]
            draw.rectangle(coordinates, outline=CLASS_INFO[class_id]['color'], width=3)

    padding = 22
    row_height = 42
    legend_width = 360
    legend_height = padding * 2 + row_height * len(CLASS_INFO)
    left = annotated.width - legend_width - 12
    top = 12
    draw.rounded_rectangle((left, top, annotated.width - 12, top + legend_height), radius=14, fill=(255, 255, 255), outline=(210, 220, 230), width=2)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 24)
    except OSError:
        font = ImageFont.load_default()
    for row, info in enumerate(CLASS_INFO.values()):
        center_x = left + padding + 12
        center_y = top + padding + row * row_height + row_height // 2
        dot_radius = 9
        draw.ellipse((center_x - dot_radius, center_y - dot_radius, center_x + dot_radius, center_y + dot_radius), fill=info['color'], outline=(25, 35, 45), width=1)
        draw.text((left + padding + 34, center_y - 14), f"{info['short']} · {info['name']}", fill=(25, 35, 45), font=font)
    return annotated


def generate_lesion_detection(uploaded_file, media_root):
    request_id = uuid.uuid4().hex
    request_root = Path(media_root) / 'lesions' / request_id
    request_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or '.jpg'
    input_path = request_root / f'input{suffix}'
    result_path = request_root / 'annotated-retinal-lesions.jpg'

    with input_path.open('wb') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    try:
        with Image.open(input_path) as image:
            image = image.convert('RGB')
            model = get_model()
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model.model.to(device)
            with MODEL_LOCK:
                prediction = model.predict(
                    source=str(input_path),
                    imgsz=1024,
                    conf=0.25,
                    iou=0.50,
                    max_det=1000,
                    device=0 if device.type == 'cuda' else 'cpu',
                    verbose=False,
                )[0]
            annotated = _draw_annotations(image, prediction)
            annotated.save(result_path, format='JPEG', quality=95, subsampling=0)
    except (UnidentifiedImageError, OSError):
        input_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        raise ValueError('The selected file could not be read as an image.') from None

    summary = {
        class_id: {'count': 0, 'average': 0.0, 'highest': 0.0}
        for class_id in CLASS_INFO
    }
    detections = []
    for box in prediction.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        if class_id in summary:
            summary[class_id]['count'] += 1
            summary[class_id]['average'] += confidence
            summary[class_id]['highest'] = max(summary[class_id]['highest'], confidence)
            detections.append({
                'class_id': class_id,
                'class_name': CLASS_INFO[class_id]['name'],
                'confidence': round(confidence, 4),
                'box': [round(value) for value in box.xyxy[0].tolist()],
            })
    for values in summary.values():
        if values['count']:
            values['average'] /= values['count']

    relative_root = Path('lesions') / request_id
    return {
        'request_id': request_id,
        'original_url': str(relative_root / input_path.name).replace('\\', '/'),
        'image_url': str(relative_root / result_path.name).replace('\\', '/'),
        'download_url': str(relative_root / result_path.name).replace('\\', '/'),
        'filename': uploaded_file.name,
        'summary': {str(class_id): values for class_id, values in summary.items()},
        'total': sum(item['count'] for item in summary.values()),
        'detections': detections,
        'device': str(device),
    }