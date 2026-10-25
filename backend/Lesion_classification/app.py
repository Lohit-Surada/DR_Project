from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from werkzeug.utils import secure_filename
import torch
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MODEL_PATH = BASE_DIR / "best.pt"
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = STATIC_DIR / "results"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
CLASS_INFO = {
    0: {"name": "Microaneurysm", "short": "MA", "color": (255, 0, 0)},
    1: {"name": "Haemorrhage", "short": "HE", "color": (0, 0, 255)},
    2: {"name": "Hard Exudate", "short": "EX", "color": (0, 255, 0)},
    3: {"name": "Soft Exudate", "short": "SE", "color": (255, 255, 0)},
}

UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "lesion-detection-local")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
model: YOLO | None = None
MODEL_ERROR: str | None = None
if MODEL_PATH.exists():
    try:
        model = YOLO(str(MODEL_PATH))
    except Exception as error:
        MODEL_ERROR = str(error)
else:
    MODEL_ERROR = f"Model file not found: {MODEL_PATH.name}"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def class_name(names: object, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, "Lesion"))
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    return "Lesion"


@app.errorhandler(413)
def file_too_large(_error):
    flash("That image is larger than 10 MB. Please choose a smaller file.", "error")
    return redirect(url_for("index"))


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/predict")
def predict():
    uploaded_file = request.files.get("image")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choose an image before running detection.", "error")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        flash("Use a JPG, JPEG, or PNG image.", "error")
        return redirect(url_for("index"))

    if model is None:
        flash(MODEL_ERROR or "The YOLO model could not be loaded.", "error")
        return redirect(url_for("index"))

    request_id = uuid.uuid4().hex
    extension = Path(secure_filename(uploaded_file.filename)).suffix.lower() or ".jpg"
    original_name = f"{request_id}{extension}"
    original_path = UPLOAD_DIR / original_name
    result_path = RESULT_DIR / f"{request_id}.jpg"

    try:
        with Image.open(uploaded_file) as image:
            image = image.convert("RGB")
            if extension == ".png":
                image.save(original_path, format="PNG", optimize=True)
            else:
                image.save(original_path, format="JPEG", quality=95, subsampling=0)
            prediction = model.predict(
                source=str(original_path), imgsz=1024, conf=0.25, iou=0.50,
                max_det=1000, device=DEVICE, verbose=False,
            )[0]
            annotated = draw_annotations(image, prediction)
            annotated.save(result_path, format="JPEG", quality=95, subsampling=0)

        summary = {class_id: {"count": 0, "average": 0.0, "highest": 0.0} for class_id in CLASS_INFO}
        for box in prediction.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            if class_id in summary:
                summary[class_id]["count"] += 1
                summary[class_id]["average"] += confidence
                summary[class_id]["highest"] = max(summary[class_id]["highest"], confidence)
        for values in summary.values():
            if values["count"]:
                values["average"] /= values["count"]
    except (UnidentifiedImageError, OSError):
        original_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        flash("The selected file could not be read as an image.", "error")
        return redirect(url_for("index"))
    except Exception as error:
        original_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        app.logger.exception("Detection failed: %s", error)
        flash("Detection could not be completed. Check that the YOLO model is valid.", "error")
        return redirect(url_for("index"))

    return render_template(
        "index.html",
        result={
            "original_url": url_for("static", filename=f"uploads/{original_name}"),
            "image_url": url_for("result_image", filename=f"{request_id}.jpg"),
            "download_url": url_for("download_result", filename=f"{request_id}.jpg"),
            "filename": secure_filename(uploaded_file.filename),
            "summary": summary,
            "total": sum(item["count"] for item in summary.values()),
        },
        class_info=CLASS_INFO,
        device=DEVICE,
    )


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


def draw_annotations(image: Image.Image, prediction) -> Image.Image:
    """Draw uncluttered lesion boxes and a clearly readable legend on the fundus image."""
    annotated = image.copy().convert("RGB")
    draw = ImageDraw.Draw(annotated)
    ref_dim = min(annotated.width, annotated.height)
    box_width = max(2, round(ref_dim * 0.0025))

    for box in prediction.boxes:
        class_id = int(box.cls[0].item())
        if class_id in CLASS_INFO:
            coordinates = [round(value) for value in box.xyxy[0].tolist()]
            draw.rectangle(coordinates, outline=CLASS_INFO[class_id]["color"], width=box_width)

    # Scale legend elements compactly to sit within the black corner background
    font_size = max(16, int(ref_dim * 0.021))
    font = _load_legend_font(font_size)

    # Display symptom names only without abbreviations
    legend_labels = [info["name"] for info in CLASS_INFO.values()]
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
            fill=info["color"],
            outline=(51, 65, 85),
            width=dot_border,
        )

        # Draw symptom name text
        text_x = center_x + dot_radius + marker_gap
        try:
            draw.text((text_x, center_y), info["name"], fill=(15, 23, 42), font=font, anchor="lm")
        except TypeError:
            bbox = draw.textbbox((0, 0), info["name"], font=font)
            text_h = bbox[3] - bbox[1]
            draw.text((text_x, center_y - text_h // 2 - bbox[1]), info["name"], fill=(15, 23, 42), font=font)

    return annotated


@app.get("/result/<filename>")
def result_image(filename):
    return send_from_directory(RESULT_DIR, secure_filename(filename))


@app.get("/download/<filename>")
def download_result(filename):
    return send_from_directory(RESULT_DIR, secure_filename(filename), as_attachment=True, download_name="annotated-retinal-lesions.jpg")


if __name__ == "__main__":
    app.run(debug=True)
