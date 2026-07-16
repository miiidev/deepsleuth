import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from pathlib import Path
import timm
import numpy as np
import random
from PIL import Image
import json
import sys
import time
import re
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed" / "images"
SPLITS_DIR = BASE_DIR / "data" / "splits"
WEIGHTS_DIR = BASE_DIR / "weights"

SEED = 42
BATCH_SIZE = 32
EPOCHS = 40
LR = 1e-4
WARMUP_EPOCHS = 2
IMG_SIZE = 299
NUM_WORKERS = 0
EARLY_STOP_PATIENCE = 7
LABEL_SMOOTHING = 0.1
GRAD_CLIP = 1.0

MANIPULATION_METHODS = ["Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures"]


def infer_method_from_path(filepath: str) -> str:
    path = Path(filepath)
    parts = path.parts
    if "real" in parts:
        return "real"
    for method in MANIPULATION_METHODS:
        if method in parts:
            return method
    return "unknown"


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


set_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
if device.type == "cuda":
    print(f"  GPU: {torch.cuda.get_device_name(0)}")


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
    """Parse filename to extract quality, method, video stem, and frame number.

    New format: {quality}_{method}_{video_stem}_f{frame_num}.jpg
    Old format: {quality}_{video_stem}_f{frame_num}.jpg
    Legacy:     {video_stem}_f{frame_num}.jpg

    Returns: (quality, method, video_stem, frame_num)
    """
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
    """Extract source video ID from a video stem.

    Fake stems: {source_id}_{target_id} (e.g., '000_003')
    Real stems: {video_id} (e.g., '000')
    """
    parts = video_stem.split("_")
    if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
        return parts[0]
    return video_stem


def extract_target_id(video_stem: str):
    """Extract target ID from a fake video stem, or None for real videos."""
    parts = video_stem.split("_")
    if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
        return parts[1]
    return None


def video_level_split(paths, labels, train_ratio=0.8, val_ratio=0.1):
    """Split data at the video source-ID level to prevent data leakage.

    Each source ID (000-999) maps to all its frames. When a source ID is
    assigned to test, ALL frames from ALL videos with that source ID go to test.

    Additionally, to prevent identity leakage via target IDs (e.g., video
    000_003.mp4 leaks identity 003), we also exclude target IDs that appear
    in the test set from the training set.
    """
    source_to_frames = {}
    all_target_ids = {}

    for p, l in zip(paths, labels):
        quality, _method, video_stem, frame_num = parse_filename(p)
        source_id = extract_source_id(video_stem)
        target_id = extract_target_id(video_stem)

        if source_id not in source_to_frames:
            source_to_frames[source_id] = {"paths": [], "labels": [], "targets": set()}
        source_to_frames[source_id]["paths"].append(p)
        source_to_frames[source_id]["labels"].append(l)

        if target_id:
            source_to_frames[source_id]["targets"].add(target_id)
            if source_id not in all_target_ids:
                all_target_ids[source_id] = set()
            all_target_ids[source_id].add(target_id)

    all_source_ids = list(source_to_frames.keys())
    random.shuffle(all_source_ids)

    n = len(all_source_ids)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_ids = set(all_source_ids[:n_train])
    val_ids = set(all_source_ids[n_train:n_train + n_val])
    test_ids = set(all_source_ids[n_train + n_val:])

    test_target_ids = set()
    for sid in test_ids:
        test_target_ids.update(source_to_frames[sid]["targets"])

    train_ids -= test_target_ids

    train_p, train_l = [], []
    val_p, val_l = [], []
    test_p, test_l = [], []

    for sid, data in source_to_frames.items():
        if sid in train_ids:
            train_p.extend(data["paths"])
            train_l.extend(data["labels"])
        elif sid in val_ids:
            val_p.extend(data["paths"])
            val_l.extend(data["labels"])
        elif sid in test_ids:
            test_p.extend(data["paths"])
            test_l.extend(data["labels"])

    combined = list(zip(train_p, train_l))
    random.shuffle(combined)
    if combined:
        train_p, train_l = zip(*combined)
        train_p, train_l = list(train_p), list(train_l)

    print(f"  Video-level split: {len(train_ids)} train IDs, "
          f"{len(val_ids)} val IDs, {len(test_ids)} test IDs")
    if test_target_ids:
        print(f"  Excluded {len(test_target_ids)} target IDs from train set")

    return (train_p, train_l), (val_p, val_l), (test_p, test_l)


def compute_class_weights(labels):
    counts = Counter(labels)
    n = len(labels)
    weights = [n / (len(counts) * counts[l]) for l in labels]
    return torch.DoubleTensor(weights)


def build_transforms():
    train_tfm = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(5),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)),
    ])

    eval_tfm = transforms.Compose([
        transforms.Resize(int(IMG_SIZE * 1.1)),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    return train_tfm, eval_tfm


def evaluate(model, loader, device, labels=None):
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
    total = 0

    with torch.no_grad():
        for images, lbls in loader:
            images, lbls = images.to(device), lbls.to(device)
            outputs = model(images)
            loss = criterion(outputs, lbls)
            total_loss += loss.item() * images.size(0)
            total += images.size(0)
            probs = torch.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(lbls.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

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
        "all_preds": all_preds,
        "all_labels": all_labels,
    }


def evaluate_per_method(model, paths, labels, transform, device):
    """Evaluate model separately for each manipulation method."""
    method_preds = {m: {"preds": [], "labels": []} for m in MANIPULATION_METHODS}
    method_preds["real"] = {"preds": [], "labels": []}

    model.eval()

    for p, l in zip(paths, labels):
        method_key = infer_method_from_path(p)

        if method_key not in method_preds:
            method_preds[method_key] = {"preds": [], "labels": []}

        img = Image.open(p).convert("RGB")
        if transform:
            img = transform(img)
        img = img.unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(img)
            _, predicted = torch.max(output, 1)

        method_preds[method_key]["preds"].append(predicted.item())
        method_preds[method_key]["labels"].append(l)

    results = {}
    for method, data in method_preds.items():
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


def train():
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Building splits...")
    all_real = sorted((DATA_DIR / "real").glob("*.jpg"))
    all_fake = []
    fake_dir = DATA_DIR / "fake"
    if fake_dir.exists():
        for method_dir in fake_dir.iterdir():
            if method_dir.is_dir():
                all_fake.extend(sorted(method_dir.glob("*.jpg")))

    all_paths = [str(p) for p in all_real] + [str(p) for p in all_fake]
    all_labels = [0] * len(all_real) + [1] * len(all_fake)

    (train_paths, train_labels), (val_paths, val_labels), (test_paths, test_labels) = video_level_split(
        all_paths, all_labels
    )

    info = {
        "seed": SEED,
        "split_type": "video_level",
        "train_real": sum(1 for l in train_labels if l == 0),
        "train_fake": sum(1 for l in train_labels if l == 1),
        "val_real": sum(1 for l in val_labels if l == 0),
        "val_fake": sum(1 for l in val_labels if l == 1),
        "test_real": sum(1 for l in test_labels if l == 0),
        "test_fake": sum(1 for l in test_labels if l == 1),
    }
    with open(SPLITS_DIR / "splits.json", "w") as f:
        json.dump(info, f, indent=2)

    print(f"  Train: {info['train_real']} real, {info['train_fake']} fake ({len(train_labels)} total)")
    print(f"  Val:   {info['val_real']} real, {info['val_fake']} fake ({len(val_labels)} total)")
    print(f"  Test:  {info['test_real']} real, {info['test_fake']} fake ({len(test_labels)} total)")

    train_tfm, eval_tfm = build_transforms()

    train_ds = FaceCropDataset(train_paths, train_labels, transform=train_tfm)
    val_ds = FaceCropDataset(val_paths, val_labels, transform=eval_tfm)
    test_ds = FaceCropDataset(test_paths, test_labels, transform=eval_tfm)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    print("\nBuilding model...")
    model = timm.create_model("xception", pretrained=True, num_classes=2)
    model = model.to(device)

    class_counts = Counter(train_labels)
    weight_tensor = torch.tensor([1.0 / class_counts[0], 1.0 / class_counts[1]], device=device)
    weight_tensor = weight_tensor / weight_tensor.sum() * 2
    criterion = nn.CrossEntropyLoss(weight=weight_tensor, label_smoothing=LABEL_SMOOTHING)

    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS - WARMUP_EPOCHS, eta_min=LR * 0.01)

    best_f1 = 0.0
    patience_counter = 0

    print(f"\nStarting training ({EPOCHS} epochs, warmup {WARMUP_EPOCHS})...\n")

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()

        if epoch <= WARMUP_EPOCHS:
            warmup_lr = LR * (epoch / WARMUP_EPOCHS)
            for pg in optimizer.param_groups:
                pg["lr"] = warmup_lr

        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            if device.type == "cuda":
                with torch.amp.autocast("cuda"):
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                optimizer.step()
            else:
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_loss = running_loss / total
        train_acc = correct / total

        if epoch > WARMUP_EPOCHS:
            scheduler.step()

        val_metrics = evaluate(model, val_loader, device)
        elapsed = time.time() - epoch_start

        current_lr = optimizer.param_groups[0]["lr"]
        improved = ""
        if val_metrics["f1"] > best_f1:
            best_f1 = val_metrics["f1"]
            patience_counter = 0
            torch.save(model.state_dict(), WEIGHTS_DIR / "xception_best.pth")
            improved = " >> BEST"
        else:
            patience_counter += 1

        print(
            f"Epoch {epoch:2d}/{EPOCHS}  "
            f"Train Loss: {train_loss:.4f}  Acc: {train_acc:.4f}  |  "
            f"Val Loss: {val_metrics['loss']:.4f}  Acc: {val_metrics['acc']:.4f}  "
            f"F1: {val_metrics['f1']:.4f}  P: {val_metrics['precision']:.4f}  R: {val_metrics['recall']:.4f}  "
            f"LR: {current_lr:.2e}  {elapsed:.1f}s{improved}"
        )

        if patience_counter >= EARLY_STOP_PATIENCE:
            print(f"\nEarly stopping at epoch {epoch} (no F1 improvement for {EARLY_STOP_PATIENCE} epochs)")
            break

    print(f"\nBest validation F1: {best_f1:.4f}")

    print("\nEvaluating on test set...")
    model.load_state_dict(torch.load(WEIGHTS_DIR / "xception_best.pth", weights_only=True))
    test_metrics = evaluate(model, test_loader, device)

    print(f"Test Accuracy:  {test_metrics['acc']:.4f}")
    print(f"Test F1:        {test_metrics['f1']:.4f}")
    print(f"Test Precision: {test_metrics['precision']:.4f}")
    print(f"Test Recall:    {test_metrics['recall']:.4f}")
    print(f"Confusion: TP={test_metrics['tp']} FP={test_metrics['fp']} FN={test_metrics['fn']} TN={test_metrics['tn']}")

    print("\nPer-method evaluation on test set...")
    method_results = evaluate_per_method(model, test_paths, test_labels, eval_tfm, device)
    for method, metrics in sorted(method_results.items()):
        print(f"  {method}: acc={metrics['acc']:.4f} ({metrics['correct']}/{metrics['count']})")

    info["test_accuracy"] = test_metrics["acc"]
    info["test_f1"] = test_metrics["f1"]
    info["test_precision"] = test_metrics["precision"]
    info["test_recall"] = test_metrics["recall"]
    info["test_tp"] = test_metrics["tp"]
    info["test_fp"] = test_metrics["fp"]
    info["test_fn"] = test_metrics["fn"]
    info["test_tn"] = test_metrics["tn"]
    info["per_method"] = method_results
    with open(SPLITS_DIR / "splits.json", "w") as f:
        json.dump(info, f, indent=2, default=str)

    print("\nDone! Best checkpoint at: weights/xception_best.pth")


if __name__ == "__main__":
    train()
