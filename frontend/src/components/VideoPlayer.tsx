import { useRef, useEffect, useCallback, useState } from "react";
import { getOriginalVideoUrl } from "../api/client";
import type { FrameFaceData } from "../api/client";

interface Props {
  taskId: string;
  videoUrl: string;
  frameFaceData: FrameFaceData[];
}

export default function VideoPlayer({ taskId, frameFaceData }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const frameMapRef = useRef<Map<number, FrameFaceData>>(new Map());

  useEffect(() => {
    const map = new Map<number, FrameFaceData>();
    for (const entry of frameFaceData) {
      map.set(entry.frame, entry);
    }
    frameMapRef.current = map;
  }, [frameFaceData]);

  const findClosestFrame = useCallback(
    (currentFrame: number): FrameFaceData | null => {
      const map = frameMapRef.current;
      if (map.size === 0) return null;
      if (map.has(currentFrame)) return map.get(currentFrame)!;

      let closest: FrameFaceData | null = null;
      let minDist = Infinity;
      for (const [frame, data] of map) {
        const dist = Math.abs(frame - currentFrame);
        if (dist < minDist) {
          minDist = dist;
          closest = data;
        }
      }
      return closest;
    },
    [],
  );

  const drawOverlay = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !showOverlay) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const fps = 30;
    const currentFrame = Math.floor(video.currentTime * fps);
    const entry = findClosestFrame(currentFrame);
    if (!entry || entry.faces.length === 0) return;

    const scaleX = canvas.width / video.videoWidth;
    const scaleY = canvas.height / video.videoHeight;

    for (const face of entry.faces) {
      const [x, y, w, h] = face.bbox;
      const sx = x * scaleX;
      const sy = y * scaleY;
      const sw = w * scaleX;
      const sh = h * scaleY;

      const isSuspicious = face.score > 0.5;

      if (face.heatmap && face.heatmap.length > 0) {
        const gridLen = Math.round(Math.sqrt(face.heatmap.length));
        const heatCanvas = document.createElement("canvas");
        heatCanvas.width = gridLen;
        heatCanvas.height = gridLen;
        const heatCtx = heatCanvas.getContext("2d")!;
        const imageData = heatCtx.createImageData(gridLen, gridLen);

        for (let i = 0; i < face.heatmap.length; i++) {
          const val = Math.max(0, Math.min(1, face.heatmap[i]));
          let r: number, g: number, b: number;

          if (val < 0.25) {
            const t = val / 0.25;
            r = 0;
            g = Math.round(t * 255);
            b = 255;
          } else if (val < 0.5) {
            const t = (val - 0.25) / 0.25;
            r = 0;
            g = 255;
            b = Math.round((1 - t) * 255);
          } else if (val < 0.75) {
            const t = (val - 0.5) / 0.25;
            r = Math.round(t * 255);
            g = 255;
            b = 0;
          } else {
            const t = (val - 0.75) / 0.25;
            r = 255;
            g = Math.round((1 - t) * 255);
            b = 0;
          }

          const alpha = Math.round((0.15 + val * 0.55) * 255);
          imageData.data[i * 4] = r;
          imageData.data[i * 4 + 1] = g;
          imageData.data[i * 4 + 2] = b;
          imageData.data[i * 4 + 3] = alpha;
        }

        heatCtx.putImageData(imageData, 0, 0);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(heatCanvas, sx, sy, sw, sh);
      } else {
        const alpha = 0.3 + Math.min(1, face.score) * 0.4;
        const r = isSuspicious ? 217 : 13;
        const g = isSuspicious ? 119 : 148;
        const b = isSuspicious ? 6 : 148;
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.fillRect(sx, sy, sw, sh);
      }

      const borderColor = isSuspicious
        ? "rgba(217, 119, 6, 0.9)"
        : "rgba(13, 148, 136, 0.9)";
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(sx, sy, sw, sh);

      const label = isSuspicious
        ? `Anomaly: ${face.score.toFixed(2)}`
        : `Appears consistent`;
      ctx.font = "bold 14px sans-serif";
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = isSuspicious
        ? "rgba(217, 119, 6, 0.85)"
        : "rgba(13, 148, 136, 0.85)";
      ctx.fillRect(sx, sy - 22, textWidth + 8, 22);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, sx + 4, sy - 6);
    }
  }, [showOverlay, findClosestFrame]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => drawOverlay();
    const onResize = () => drawOverlay();

    video.addEventListener("timeupdate", onTimeUpdate);
    window.addEventListener("resize", onResize);
    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      window.removeEventListener("resize", onResize);
    };
  }, [drawOverlay]);

  useEffect(() => {
    if (showOverlay) drawOverlay();
  }, [showOverlay, drawOverlay]);

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden">
      <div className="relative">
        <video
          ref={videoRef}
          src={getOriginalVideoUrl(taskId)}
          controls
          className="w-full aspect-video bg-black"
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ display: showOverlay ? "block" : "none" }}
        />
      </div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
        <span className="text-sm text-gray-400">Overlay</span>
        <button
          onClick={() => setShowOverlay((v) => !v)}
          className={`relative w-14 h-7 rounded-full transition-colors shrink-0 ${
            showOverlay ? "bg-purple-600" : "bg-gray-700"
          }`}
        >
          <span
            className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full transition-transform ${
              showOverlay ? "translate-x-7" : "translate-x-0"
            }`}
          />
        </button>
      </div>
    </div>
  );
}
