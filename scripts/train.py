import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from pathlib import Path
import timm
import numpy as np
import random
from PIL import Image
import json
import sys
import time
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


def stratified_split(paths, labels, train_ratio=0.8, val_ratio=0.1):
    by_class = {}
    for p, l in zip(paths, labels):
        by_class.setdefault(l, []).append(p)

    train_p, train_l, val_p, val_l, test_p, test_l = [], [], [], [], [], []

    for cls, cls_paths in by_class.items():
        n = len(cls_paths)
        idxs = list(range(n))
        random.shuffle(idxs)

        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        for i in idxs[:n_train]:
            train_p.append(cls_paths[i])
            train_l.append(cls)
        for i in idxs[n_train:n_train + n_val]:
            val_p.append(cls_paths[i])
            val_l.append(cls)
        for i in idxs[n_train + n_val:]:
            test_p.append(cls_paths[i])
            test_l.append(cls)

    combined = list(zip(train_p, train_l))
    random.shuffle(combined)
    train_p, train_l = zip(*combined) if combined else ([], [])

    return (list(train_p), list(train_l)), (val_p, val_l), (test_p, test_l)


def compute_class_weights(labels):
    counts = Counter(labels)
    n = len(labels)
    weights = [n / (len(counts) * counts[l]) for l in labels]
    return torch.DoubleTensor(weights)


def build_transforms():
    train_tfm = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.RandomGrayscale(p=0.1),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
    ])

    eval_tfm = transforms.Compose([
        transforms.Resize(int(IMG_SIZE * 1.1)),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    return train_tfm, eval_tfm


def evaluate(model, loader, device):
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []
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
            probs = torch.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
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
    }


def train():
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Building splits...")
    all_real = sorted((DATA_DIR / "real").glob("*.jpg"))
    all_fake = sorted((DATA_DIR / "fake").glob("*.jpg"))

    all_paths = [str(p) for p in all_real] + [str(p) for p in all_fake]
    all_labels = [0] * len(all_real) + [1] * len(all_fake)

    (train_paths, train_labels), (val_paths, val_labels), (test_paths, test_labels) = stratified_split(
        all_paths, all_labels
    )

    info = {
        "seed": SEED,
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

    sample_weights = compute_class_weights(train_labels)
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=NUM_WORKERS)
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

    info["test_accuracy"] = test_metrics["acc"]
    info["test_f1"] = test_metrics["f1"]
    info["test_precision"] = test_metrics["precision"]
    info["test_recall"] = test_metrics["recall"]
    with open(SPLITS_DIR / "splits.json", "w") as f:
        json.dump(info, f, indent=2)

    print("\nDone! Best checkpoint at: weights/xception_best.pth")


if __name__ == "__main__":
    train()
