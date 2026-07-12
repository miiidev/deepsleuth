import { useState, useRef, type ChangeEvent, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { uploadVideo } from "../api/client";

const ALLOWED = ["video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"];
const MAX_SIZE = 500 * 1024 * 1024;

export default function Upload() {
  const navigate = useNavigate();
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function valid(f: File): boolean {
    if (!ALLOWED.includes(f.type)) return false;
    if (f.size > MAX_SIZE) return false;
    return true;
  }

  function handleFile(f: File) {
    setError("");
    if (!valid(f)) {
      setError("Only MP4/MOV/WEBM/AVI up to 500MB allowed.");
      return;
    }
    setFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const { task_id } = await uploadVideo(file);
      navigate(`/processing/${task_id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function onSelect(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }

  return (
    <div className="w-full max-w-lg mx-auto text-center">
      <h2 className="text-2xl font-semibold mb-2">Upload a Video</h2>
      <p className="text-gray-500 mb-8 text-sm">Max 3 minutes · MP4, MOV, WEBM, AVI</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 cursor-pointer transition-colors ${
          drag
            ? "border-purple-500 bg-purple-500/10"
            : "border-gray-700 hover:border-gray-500"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.webm,.avi"
          className="hidden"
          onChange={onSelect}
        />
        {file ? (
          <div>
            <p className="text-lg font-medium">{file.name}</p>
            <p className="text-sm text-gray-500 mt-1">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          </div>
        ) : (
          <div>
            <p className="text-5xl mb-3 text-gray-600">+</p>
            <p className="text-gray-400">Drop a video here or click to browse</p>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="mt-6 w-full py-3 rounded-lg font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Uploading…" : "Analyze Video"}
      </button>
    </div>
  );
}
