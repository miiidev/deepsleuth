"""
Usage:
    cd backend
    .\venv\Scripts\python ..\scripts\convert_onnx.py
"""
import torch
import timm
import numpy as np
from pathlib import Path


def main():
    weights_dir = Path(__file__).resolve().parent.parent / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = weights_dir / "xception_best.pth"
    out_path = str(weights_dir / "xception_ffpp.onnx")

    model = timm.create_model("xception", pretrained=False, num_classes=2)
    model.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
    model.eval()

    dummy = torch.randn(1, 3, 299, 299)

    torch.onnx.export(
        model,
        dummy,
        out_path,
        input_names=["input"],
        output_names=["output"],
        opset_version=18,
    )

    import onnxruntime as ort
    session = ort.InferenceSession(out_path)
    out = session.run(None, {"input": dummy.numpy().astype(np.float32)})
    print("ONNX export OK. Output shape:", out[0].shape)
    print("Sample output:", out[0][0])


if __name__ == "__main__":
    main()
