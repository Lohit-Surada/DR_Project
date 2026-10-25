import glob
import os
import uuid
from pathlib import Path
from threading import RLock

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.data.augment import LetterBox


IMAGE_SIZE = 1024
TARGET_LAYER_INDEX = 16
TOP_K = 20
CONF_THRESHOLD = 0.05
CAM_ALPHA = 0.30
ATTENTION_ALPHA = 0.30
ATTENTION_SIZE = 640
FINAL_WIDTH = 2048
FINAL_HEIGHT = 705

CLASS_NAMES = {
    0: 'Microaneurysm',
    1: 'Haemorrhage',
    2: 'Hard Exudate',
    3: 'Soft Exudate',
}

LESION_COLORS = {
    0: (0, 255, 255),
    1: (255, 0, 0),
    2: (255, 255, 0),
    3: (0, 255, 0),
}

MODEL_PATH = Path(__file__).resolve().parent.parent / 'Lesion_classification' / 'best.pt'
MODEL_LOCK = RLock()
MODEL = None


def get_model():
    global MODEL
    if MODEL is None:
        with MODEL_LOCK:
            if MODEL is None:
                if not MODEL_PATH.exists():
                    raise FileNotFoundError(f'YOLO model not found: {MODEL_PATH}')
                MODEL = YOLO(str(MODEL_PATH))
    return MODEL


class GradCAMRunner:
    def __init__(self, model, device):
        self.model = model
        self.device = device
        self.activations = None
        self.gradients = None

    def _forward_hook(self, module, inputs, output):
        if isinstance(output, torch.Tensor):
            self.activations = output
        elif isinstance(output, (tuple, list)):
            self.activations = next(
                (item for item in output if isinstance(item, torch.Tensor) and item.ndim == 4),
                None,
            )

    def _backward_hook(self, module, grad_input, grad_output):
        if isinstance(grad_output, torch.Tensor):
            self.gradients = grad_output
        elif isinstance(grad_output, (tuple, list)):
            self.gradients = next(
                (item for item in grad_output if isinstance(item, torch.Tensor) and item.ndim == 4),
                None,
            )

    def _prepare_input(self, original_bgr):
        backend_model = self.model.model
        stride = int(backend_model.stride.max())
        letterbox = LetterBox(new_shape=(IMAGE_SIZE, IMAGE_SIZE), auto=False, stride=stride)
        resized_bgr = letterbox(image=original_bgr)
        resized_rgb = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        input_tensor = torch.from_numpy(resized_rgb.transpose(2, 0, 1)).float() / 255.0
        input_tensor = input_tensor.unsqueeze(0).to(self.device)
        input_tensor.requires_grad_(True)
        return input_tensor

    def _raw_scores(self, input_tensor):
        output = self.model.model(input_tensor)
        if not isinstance(output, tuple) or len(output) < 2:
            raise RuntimeError('Unexpected YOLO output format; raw Grad-CAM scores are unavailable.')
        try:
            raw_scores = output[1]['one2many']['scores']
        except (KeyError, TypeError):
            raise RuntimeError('YOLO output does not expose one2many scores for Grad-CAM.') from None
        if not raw_scores.requires_grad:
            raise RuntimeError('YOLO raw scores are detached; the Grad-CAM graph cannot be differentiated.')
        return raw_scores

    def _calculate_class_cam(self, input_tensor, target_layer, class_id):
        self.activations = None
        self.gradients = None
        backend_model = self.model.model
        backend_model.zero_grad(set_to_none=True)
        if input_tensor.grad is not None:
            input_tensor.grad.zero_()

        with torch.enable_grad():
            raw_scores = self._raw_scores(input_tensor)
            class_scores = raw_scores[0, class_id]
            probabilities = torch.sigmoid(class_scores)
            k = min(TOP_K, probabilities.numel())
            _, top_indices = torch.topk(probabilities, k=k)
            target = probabilities[top_indices].sum()
            if not target.requires_grad:
                raise RuntimeError('Grad-CAM target is detached from the YOLO computation graph.')
            target.backward()

        if self.activations is None or self.gradients is None:
            raise RuntimeError('The selected YOLO layer did not produce Grad-CAM activations and gradients.')

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1, keepdim=True))[0, 0]
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        cam = cam.detach().cpu().numpy()
        return cv2.resize(cam, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def _cam_to_original(cam, original_w, original_h):
        scale = min(IMAGE_SIZE / original_w, IMAGE_SIZE / original_h)
        new_w = int(round(original_w * scale))
        new_h = int(round(original_h * scale))
        pad_x = (IMAGE_SIZE - new_w) // 2
        pad_y = (IMAGE_SIZE - new_h) // 2
        cam_crop = cam[pad_y:pad_y + new_h, pad_x:pad_x + new_w]
        return cv2.resize(cam_crop, (original_w, original_h), interpolation=cv2.INTER_LINEAR)

    def generate_gradcam(self, original_bgr, detections):
        backend_model = self.model.model
        backend_model.eval()
        layers = backend_model.model
        if TARGET_LAYER_INDEX >= len(layers):
            raise RuntimeError(
                f'YOLO target layer {TARGET_LAYER_INDEX} is unavailable; model has {len(layers)} layers.'
            )

        input_tensor = self._prepare_input(original_bgr)
        target_layer = layers[TARGET_LAYER_INDEX]
        forward_handle = target_layer.register_forward_hook(self._forward_hook)
        backward_handle = target_layer.register_full_backward_hook(self._backward_hook)
        try:
            with torch.enable_grad():
                raw_scores = self._raw_scores(input_tensor)
                raw_probabilities = torch.sigmoid(raw_scores)

            detected_classes = sorted({item['class_id'] for item in detections})
            if not detected_classes:
                strongest_class = int(raw_probabilities.max(dim=2).values.argmax())
                detected_classes = [strongest_class]

            height, width = original_bgr.shape[:2]
            global_cam = np.zeros((height, width), dtype=np.float32)
            class_cams = {}
            for class_id in detected_classes:
                cam = self._calculate_class_cam(input_tensor, target_layer, class_id)
                class_cam = self._cam_to_original(cam, width, height)
                class_cams[class_id] = class_cam
                global_cam = np.maximum(global_cam, class_cam)
        finally:
            forward_handle.remove()
            backward_handle.remove()

        global_cam = (global_cam - global_cam.min()) / (global_cam.max() - global_cam.min() + 1e-8)
        heatmap = cv2.applyColorMap((global_cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
        overlay = cv2.addWeighted(original_rgb, 1.0 - CAM_ALPHA, heatmap, CAM_ALPHA, 0)
        return overlay, detected_classes


def _add_title(image, title):
    output = image.copy()
    cv2.rectangle(output, (0, 0), (output.shape[1], 48), (0, 0, 0), -1)
    cv2.putText(output, title, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
    return output


def _retinal_attention(original_rgb):
    attention_rgb = cv2.resize(original_rgb, (ATTENTION_SIZE, ATTENTION_SIZE), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(attention_rgb, cv2.COLOR_RGB2GRAY)
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 7)
    attention = cv2.GaussianBlur(cv2.absdiff(enhanced, blur), (0, 0), 3)
    attention = cv2.normalize(attention, None, 0, 255, cv2.NORM_MINMAX)
    heatmap = cv2.applyColorMap(attention.astype(np.uint8), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(attention_rgb, 1.0 - ATTENTION_ALPHA, heatmap, ATTENTION_ALPHA, 0)


def _find_feature_visualization(feature_root, input_path):
    image_paths = [
        path for path in glob.glob(os.path.join(str(feature_root), '**', '*'), recursive=True)
        if Path(path).suffix.lower() in {'.jpg', '.jpeg', '.png'} and os.path.abspath(path) != os.path.abspath(input_path)
    ]
    preferred = [
        path for path in image_paths
        if any(keyword in Path(path).name.lower() for keyword in ('cam', 'feature', 'visual'))
    ]
    candidates = preferred or image_paths
    if not candidates:
        raise RuntimeError('Ultralytics did not produce a feature visualization image.')
    return max(candidates, key=os.path.getmtime)


def generate_visualization(uploaded_file, media_root):
    request_id = uuid.uuid4().hex
    request_root = Path(media_root) / 'gradcam' / request_id
    input_dir = request_root / 'input'
    feature_dir = request_root / 'feature'
    output_dir = request_root / 'outputs'
    input_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.name).suffix.lower()
    input_path = input_dir / f'input{suffix}'
    with input_path.open('wb') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    original_bgr = cv2.imread(str(input_path))
    if original_bgr is None:
        raise ValueError('The uploaded file could not be read as an image.')

    model = get_model()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.model.to(device)
    with MODEL_LOCK:
        result = model.predict(
            source=str(input_path), imgsz=IMAGE_SIZE, conf=CONF_THRESHOLD,
            device=0 if device.type == 'cuda' else 'cpu', verbose=False,
        )[0]
        detections = []
        if result.boxes is not None:
            for index in range(len(result.boxes)):
                class_id = int(result.boxes.cls[index])
                detections.append({
                    'class_id': class_id,
                    'class_name': CLASS_NAMES.get(class_id, str(class_id)),
                    'confidence': round(float(result.boxes.conf[index]), 4),
                })

        original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
        runner = GradCAMRunner(model, device)
        gradcam_rgb, detected_classes = runner.generate_gradcam(original_bgr, detections)
        attention_rgb = _retinal_attention(original_rgb)
        model.predict(
            source=str(input_path), imgsz=IMAGE_SIZE, conf=CONF_THRESHOLD,
            visualize=True, save=True, project=str(feature_dir), name='run', exist_ok=True,
            device=0 if device.type == 'cuda' else 'cpu', verbose=False,
        )

    feature_path = _find_feature_visualization(feature_dir, input_path)
    feature_bgr = cv2.imread(feature_path)
    if feature_bgr is None:
        raise RuntimeError('The generated feature visualization could not be read.')
    feature_rgb = cv2.cvtColor(feature_bgr, cv2.COLOR_BGR2RGB)

    panel_width = FINAL_WIDTH // 4
    # Clean panels (no title bar) — used for individual PDF report images
    clean_panels = [
        cv2.resize(original_rgb, (panel_width, FINAL_HEIGHT), interpolation=cv2.INTER_AREA),
        cv2.resize(gradcam_rgb, (panel_width, FINAL_HEIGHT), interpolation=cv2.INTER_AREA),
        cv2.resize(attention_rgb, (panel_width, FINAL_HEIGHT), interpolation=cv2.INTER_AREA),
        cv2.resize(feature_rgb, (FINAL_WIDTH - 3 * panel_width, FINAL_HEIGHT), interpolation=cv2.INTER_AREA),
    ]
    # Titled panels — used only for the combined strip (web UI reference)
    titled_panels = [
        _add_title(clean_panels[0], '1. INPUT FUNDUS'),
        _add_title(clean_panels[1], '2. TRUE YOLO26 GRAD-CAM'),
        _add_title(clean_panels[2], '3. RETINAL ATTENTION MAP'),
        _add_title(clean_panels[3], '4. YOLO26 FEATURE VISUALIZATION'),
    ]
    combined = np.hstack(titled_panels)

    filenames = [
        '01_INPUT_FUNDUS.png',
        '02_TRUE_YOLO26_GRADCAM.png',
        '03_RETINAL_ATTENTION.png',
        '04_YOLO26_FEATURE_VISUALIZATION.png',
    ]
    # Write individual panels WITHOUT title bar for clean PDF rendering
    for panel, filename in zip(clean_panels, filenames):
        cv2.imwrite(str(output_dir / filename), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR))
    combined_filename = 'FINAL_4_PANEL_YOLO26_VISUALIZATION.png'
    cv2.imwrite(str(output_dir / combined_filename), cv2.cvtColor(combined, cv2.COLOR_RGB2BGR))

    relative_output = Path('gradcam') / request_id / 'outputs'
    return {
        'request_id': request_id,
        'detected_classes': [
            {'class_id': class_id, 'class_name': CLASS_NAMES.get(class_id, str(class_id))}
            for class_id in detected_classes
        ],
        'detections': detections,
        'files': {
            'input_fundus': str(relative_output / filenames[0]).replace(os.sep, '/'),
            'gradcam': str(relative_output / filenames[1]).replace(os.sep, '/'),
            'attention': str(relative_output / filenames[2]).replace(os.sep, '/'),
            'feature_visualization': str(relative_output / filenames[3]).replace(os.sep, '/'),
            'combined': str(relative_output / combined_filename).replace(os.sep, '/'),
        },
    }