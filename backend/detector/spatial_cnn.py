import numpy as np
import cv2
import os
import torch
from app.config import settings
from detector.face_detection import FaceRegion
from detector.xception import Xception

_model = None
_device = None
_feature_maps = None
_gradients = None
_forward_handle = None
_backward_handle = None

EYES = np.array([
    33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246,
    362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398,
])
NOSE = np.array([
    1, 2, 98, 327, 4, 5, 195, 197, 19, 94, 168, 6, 197, 195, 399, 437,
])
MOUTH = np.array([
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185,
    78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191,
])
FOREHEAD = np.array([
    10, 151, 9, 8, 107, 66, 105, 63, 70, 336, 296, 334, 293, 300, 285, 282, 283, 276,
])
CHEEKS = np.array([
    36, 205, 206, 207, 187, 123, 116, 117, 118, 119, 100,
    266, 425, 426, 427, 411, 352, 345, 346, 347, 348, 329,
])
JAWLINE = np.array([
    152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
])

REGIONS = {
    "eyes": EYES,
    "nose": NOSE,
    "mouth": MOUTH,
    "forehead": FOREHEAD,
    "cheeks": CHEEKS,
    "jawline": JAWLINE,
}


def _load_model():
    global _model, _device, _forward_handle, _backward_handle
    if _model is not None:
        return _model

    weights_path = os.path.join(settings.WEIGHTS_DIR, "xception_best.pth")
    if not os.path.exists(weights_path):
        return None

    _device = torch.device("cpu")
    _model = Xception(num_classes=2)
    checkpoint = torch.load(weights_path, map_location=_device, weights_only=False)
    if "model_state_dict" in checkpoint:
        _model.load_state_dict(checkpoint["model_state_dict"])
    elif "state_dict" in checkpoint:
        _model.load_state_dict(checkpoint["state_dict"])
    else:
        _model.load_state_dict(checkpoint)
    _model.to(_device)
    _model.eval()

    def forward_hook(module, input, output):
        global _feature_maps
        _feature_maps = output.detach()

    def backward_hook(module, grad_input, grad_output):
        global _gradients
        _gradients = grad_output[0].detach()

    _forward_handle = _model.block12.register_forward_hook(forward_hook)
    _backward_handle = _model.block12.register_full_backward_hook(backward_hook)

    return _model


def preprocess_face(face: np.ndarray, size: int = 299) -> torch.Tensor:
    face = cv2.resize(face, (size, size))
    face = face.astype(np.float32) / 127.5 - 1.0
    face = np.transpose(face, (2, 0, 1))
    return torch.from_numpy(face).unsqueeze(0).float()


def compute_gradcam(face_tensor: torch.Tensor, target_class: int = 1) -> np.ndarray:
    global _feature_maps, _gradients

    _feature_maps = None
    _gradients = None

    face_tensor = face_tensor.to(_device)
    face_tensor.requires_grad_(True)

    output = _model(face_tensor)

    _model.zero_grad()
    one_hot = torch.zeros_like(output)
    one_hot[0, target_class] = 1.0
    output.backward(gradient=one_hot, retain_graph=True)

    if _feature_maps is None or _gradients is None:
        return np.zeros((56, 56), dtype=np.float32)

    weights = _gradients.mean(dim=(2, 3), keepdim=True)
    cam = torch.sum(weights * _feature_maps, dim=1, keepdim=True)
    cam = torch.relu(cam)

    cam = cam.squeeze().cpu().numpy()
    cam = cv2.resize(cam, (56, 56))
    cam_min = cam.min()
    cam_max = cam.max()
    if cam_max - cam_min > 1e-8:
        cam = (cam - cam_min) / (cam_max - cam_min)
    else:
        cam = np.zeros_like(cam)
    return cam.astype(np.float32)


def _region_scores(heatmap: np.ndarray, landmarks: np.ndarray, crop_w: int, crop_h: int) -> dict[str, float]:
    grid = 56
    region_scores = {}
    for name, indices in REGIONS.items():
        valid = indices[indices < len(landmarks)]
        if len(valid) == 0:
            region_scores[name] = 0.0
            continue
        pts = landmarks[valid]
        cols = (pts[:, 0] / crop_w) * grid
        rows = (pts[:, 1] / crop_h) * grid
        c_min = max(0, int(cols.min()) - 1)
        c_max = min(grid, int(cols.max()) + 2)
        r_min = max(0, int(rows.min()) - 1)
        r_max = min(grid, int(rows.max()) + 2)
        if c_min >= c_max or r_min >= r_max:
            region_scores[name] = 0.0
            continue
        patch = heatmap[r_min:r_max, c_min:c_max]
        region_scores[name] = float(np.mean(patch))
    return region_scores


def run(faces: list[FaceRegion]) -> tuple[float, list[float], list[list[float]], list[dict[str, float]]]:
    model = _load_model()
    if model is None:
        n = len(faces)
        return 0.5, [0.5] * n, [[] for _ in range(n)], [{} for _ in range(n)]

    scores = []
    heatmaps = []
    regions_list = []
    for face_region in faces:
        inp = preprocess_face(face_region.crop)
        with torch.enable_grad():
            cam = compute_gradcam(inp, target_class=1)

        output = model(inp.to(_device).detach())
        prob = torch.softmax(output, dim=1)
        fake_prob = float(prob[0, 1])
        scores.append(fake_prob)
        heatmaps.append(cam.flatten().tolist())

        ch, cw = face_region.crop.shape[:2]
        region_scores = _region_scores(cam, face_region.landmarks, cw, ch)
        regions_list.append(region_scores)

    mean_score = np.mean(scores) if scores else 0.5
    return float(mean_score), scores, heatmaps, regions_list
