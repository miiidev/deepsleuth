import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from pathlib import Path
import timm
import numpy as np
import re
import json
import sys
from collections import Counter
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed" / "images"
SPLITS_DIR = BASE_DIR / "data" / "splits"
WEIGHTS_DIR = BASE_DIR / "weights"

IMG_SIZE = 299
BATCH_SIZE = 32
NUM_WORKERS = 0
LABEL_SMOOTHING = 0.1

MANIPULATION_METHODS = ["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"]


class FaceCropDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        label = self.labels[idx]
        if self.transform:
            img = self.transform(img)
        return img, label


def parse_filename(filepath: str):
    name = Path(filepath).stem

    m_new = re.match(r"^(c\d+)_(\w+?)_(.+?)_f(\d+)$", name)
    if m_new:
        return m_new.group(1), m_new.group(2), m_new.group(3), int(m_new.group(4))

    m_old_quality = re.match(r"^(c\d+)_(.+?)_f(\d+)$", name)
    if m_old_quality:
        return m_old_quality.group(1), None, m_old_quality.group(2), int(m_old_quality.group(3))

    m_legacy = re.match(r"^(.+?)_f(\d+)$", name)
    if m_legacy:
        return None, None, m_legacy.group(1), int(m_legacy.group(2))

    return None, None, name, None


def extract_source_id(video_stem: str):
    parts = video_stem.split("_")
    if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
        return parts[0]
    return video_stem


def infer_method_from_path(filepath: str) -> str:
    path = Path(filepath)
    parts = path.parts
    if "real" in parts:
        return "real"
    for method in MANIPULATION_METHODS:
        if method in parts:
            return method
    return "unknown"


def load_all_paths():
    all_paths = []
    all_labels = []

    real_dir = DATA_DIR / "real"
    if real_dir.exists():
        for p in sorted(real_dir.glob("*.jpg")):
            all_paths.append(str(p))
            all_labels.append(0)

    fake_dir = DATA_DIR / "fake"
    if fake_dir.exists():
        for method_dir in fake_dir.iterdir():
            if method_dir.is_dir():
                for p in sorted(method_dir.glob("*.jpg")):
                    all_paths.append(str(p))
                    all_labels.append(1)

    return all_paths, all_labels


def build_eval_transform():
    return transforms.Compose([
        transforms.Resize(int(IMG_SIZE * 1.1)),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])


def load_model(checkpoint_path: Path):
    model = timm.create_model("xception", pretrained=False, num_classes=2)
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    return model


def video_level_split(paths, labels):
    source_to_frames = {}

    for p, l in zip(paths, labels):
        quality, _method, video_stem, frame_num = parse_filename(p)
        source_id = extract_source_id(video_stem)

        if source_id not in source_to_frames:
            source_to_frames[source_id] = {"paths": [], "labels": [], "targets": set()}
        source_to_frames[source_id]["paths"].append(p)
        source_to_frames[source_id]["labels"].append(l)

        target_id_parts = video_stem.split("_")
        if len(target_id_parts) == 2:
            source_to_frames[source_id]["targets"].add(target_id_parts[1])

    all_source_ids = list(source_to_frames.keys())

    test_ids = set(all_source_ids[int(len(all_source_ids) * 0.9):])

    test_target_ids = set()
    for sid in test_ids:
        test_target_ids.update(source_to_frames[sid]["targets"])

    test_paths, test_labels = [], []
    for sid, data in source_to_frames.items():
        if sid in test_ids:
            test_paths.extend(data["paths"])
            test_labels.extend(data["labels"])

    return test_paths, test_labels


def evaluate_overall(model, loader, device):
    model.eval()
    all_preds = []
    all_labels = []
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
    total = 0

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item() * images.size(0)
            total += images.size(0)
            _, predicted = torch.max(outputs, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    acc = (all_preds == all_labels).mean()
    avg_loss = total_loss / max(total, 1)

    tp = int(((all_preds == 1) & (all_labels == 1)).sum())
    fp = int(((all_preds == 1) & (all_labels == 0)).sum())
    fn = int(((all_preds == 0) & (all_labels == 1)).sum())
    tn = int(((all_preds == 0) & (all_labels == 0)).sum())

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)

    return {
        "loss": avg_loss,
        "acc": acc,
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def evaluate_by_quality(model, paths, labels, transform, device):
    quality_data = {}
    for p, l in zip(paths, labels):
        quality, _method, video_stem, frame_num = parse_filename(p)
        q = quality or "unknown"
        if q not in quality_data:
            quality_data[q] = {"preds": [], "labels": []}
        quality_data[q]["labels"].append(l)

    model.eval()
    for p, l in zip(paths, labels):
        quality, _method, video_stem, frame_num = parse_filename(p)
        q = quality or "unknown"

        img = Image.open(p).convert("RGB")
        if transform:
            img = transform(img)
        img = img.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(img)
            _, predicted = torch.max(output, 1)

        quality_data[q]["preds"].append(predicted.item())

    results = {}
    for q, data in quality_data.items():
        preds = np.array(data["preds"])
        lbls = np.array(data["labels"])
        acc = (preds == lbls).mean()
        results[q] = {
            "acc": float(acc),
            "count": len(preds),
            "correct": int((preds == lbls).sum()),
        }

    return results


def evaluate_by_method(model, paths, labels, transform, device):
    method_data = {}
    for method in MANIPULATION_METHODS:
        method_data[method] = {"preds": [], "labels": []}
    method_data["real"] = {"preds": [], "labels": []}

    for p, l in zip(paths, labels):
        method_key = infer_method_from_path(p)

        if method_key not in method_data:
            method_data[method_key] = {"preds": [], "labels": []}

        method_data[method_key]["labels"].append(l)

        img = Image.open(p).convert("RGB")
        if transform:
            img = transform(img)
        img = img.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(img)
            _, predicted = torch.max(output, 1)

        method_data[method_key]["preds"].append(predicted.item())

    results = {}
    for method, data in method_data.items():
        if not data["preds"]:
            continue
        preds = np.array(data["preds"])
        lbls = np.array(data["labels"])
        acc = (preds == lbls).mean()
        results[method] = {
            "acc": float(acc),
            "count": len(preds),
            "correct": int((preds == lbls).sum()),
        }

    return results


def main():
    checkpoint = WEIGHTS_DIR / "xception_best.pth"
    if not checkpoint.exists():
        print(f"No checkpoint found at {checkpoint}")
        print("Run scripts/train.py first to train a model.")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Loading model...")
    model = load_model(checkpoint)
    model = model.to(device)

    print("Loading data...")
    all_paths, all_labels = load_all_paths()
    print(f"  Total: {len(all_paths)} frames ({sum(1 for l in all_labels if l == 0)} real, {sum(1 for l in all_labels if l == 1)} fake)")

    test_paths, test_labels = video_level_split(all_paths, all_labels)
    print(f"  Test set: {len(test_labels)} frames")

    transform = build_eval_transform()
    test_ds = FaceCropDataset(test_paths, test_labels, transform=transform)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    print("\nOverall test metrics:")
    overall = evaluate_overall(model, test_loader, device)
    print(f"  Accuracy:  {overall['acc']:.4f}")
    print(f"  F1:        {overall['f1']:.4f}")
    print(f"  Precision: {overall['precision']:.4f}")
    print(f"  Recall:    {overall['recall']:.4f}")
    print(f"  Confusion: TP={overall['tp']} FP={overall['fp']} FN={overall['fn']} TN={overall['tn']}")

    print("\nPer-quality breakdown:")
    quality_metrics = evaluate_by_quality(model, test_paths, test_labels, transform, device)
    for q, metrics in sorted(quality_metrics.items()):
        print(f"  {q}: acc={metrics['acc']:.4f} ({metrics['correct']}/{metrics['count']})")

    print("\nPer-method breakdown:")
    method_metrics = evaluate_by_method(model, test_paths, test_labels, transform, device)
    for method, metrics in sorted(method_metrics.items()):
        print(f"  {method}: acc={metrics['acc']:.4f} ({metrics['correct']}/{metrics['count']})")

    results = {
        "checkpoint": str(checkpoint),
        "overall": overall,
        "per_quality": quality_metrics,
        "per_method": method_metrics,
    }
    output_path = SPLITS_DIR / "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
