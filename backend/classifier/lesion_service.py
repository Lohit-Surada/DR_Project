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


def _load_legend_font(size: int):
    candidates = [
        'arialbd.ttf',
        'Arial-Bold.ttf',
        'segoeuib.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/segoeui.ttf',
        'arial.ttf',
        'segoeui.ttf',
        'DejaVuSans-Bold.ttf',
        'DejaVuSans.ttf',
        'LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/System/Library/Fonts/HelveticaNeue.ttc',
        '/Library/Fonts/Arial.ttf',
        'Helvetica.ttc',
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_annotations(image, prediction):
    annotated = image.copy().convert('RGB')
    draw = ImageDraw.Draw(annotated)
    ref_dim = min(annotated.width, annotated.height)
    box_width = max(2, round(ref_dim * 0.0025))

    for box in prediction.boxes:
        class_id = int(box.cls[0].item())
        if class_id in CLASS_INFO:
            coordinates = [round(value) for value in box.xyxy[0].tolist()]
            draw.rectangle(coordinates, outline=CLASS_INFO[class_id]['color'], width=box_width)

    # Scale legend elements compactly to sit within the black corner background
    font_size = max(16, int(ref_dim * 0.021))
    font = _load_legend_font(font_size)

    # Display symptom names only without abbreviations
    legend_labels = [info['name'] for info in CLASS_INFO.values()]
    max_label_width = max(
        (draw.textbbox((0, 0), label, font=font)[2] - draw.textbbox((0, 0), label, font=font)[0])
        for label in legend_labels
    )

    padding_x = max(10, int(font_size * 0.45))
    padding_y = max(8, int(font_size * 0.35))
    dot_radius = max(5, int(font_size * 0.26))
    marker_gap = max(6, int(font_size * 0.30))
    row_spacing = max(4, int(font_size * 0.20))
    row_height = font_size + row_spacing

    legend_width = padding_x * 2 + dot_radius * 2 + marker_gap + max_label_width
    legend_height = padding_y * 2 + (len(CLASS_INFO) - 1) * row_height + font_size

    margin = max(6, int(ref_dim * 0.008))
    right = annotated.width - margin
    left = max(margin, right - legend_width)
    top = margin
    bottom = top + legend_height

    card_radius = max(6, int(font_size * 0.25))
    card_border_width = max(1, int(font_size * 0.05))
    dot_border = 1

    # Clean white background card with slate border
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=card_radius,
        fill=(255, 255, 255),
        outline=(203, 213, 225),
        width=card_border_width,
    )

    for row, info in enumerate(CLASS_INFO.values()):
        center_x = left + padding_x + dot_radius
        center_y = top + padding_y + row * row_height + font_size // 2

        # Draw colored marker dot
        draw.ellipse(
            (center_x - dot_radius, center_y - dot_radius, center_x + dot_radius, center_y + dot_radius),
            fill=info['color'],
            outline=(51, 65, 85),
            width=dot_border,
        )

        # Draw symptom name text
        text_x = center_x + dot_radius + marker_gap
        try:
            draw.text((text_x, center_y), info['name'], fill=(15, 23, 42), font=font, anchor='lm')
        except TypeError:
            bbox = draw.textbbox((0, 0), info['name'], font=font)
            text_h = bbox[3] - bbox[1]
            draw.text((text_x, center_y - text_h // 2 - bbox[1]), info['name'], fill=(15, 23, 42), font=font)

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
