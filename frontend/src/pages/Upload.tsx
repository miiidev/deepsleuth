import { useState, useRef, type ChangeEvent, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { uploadVideo } from "../api/client";
import Typewriter from "../components/Typewriter";

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
      <h2 className="text-2xl font-heading tracking-wider text-[#00FF41] mb-2 min-h-[2rem]"><Typewriter text="█ UPLOAD" /></h2>
      <p className="text-gray-600 font-mono text-sm mb-8">Max 3 minutes &middot; MP4, MOV, WEBM, AVI</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 cursor-pointer transition-all duration-200 ${
          drag
            ? "border-[#00FF41] bg-[#00FF41]/5 neon-border"
            : "border-gray-700 hover:border-[#00FF41]"
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
            <p className="text-lg font-mono text-gray-300">{file.name}</p>
            <p className="text-sm font-mono text-gray-600 mt-1">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          </div>
        ) : (
          <div>
            <p className="text-5xl mb-3 text-gray-700 font-mono neon-glow-sm">+</p>
            <p className="text-gray-500 font-mono text-sm">Drop a video here or click to browse</p>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-[#FF3333] font-mono text-sm neon-glow-sm">{error}</p>}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="mt-6 w-full py-3 rounded-lg font-mono text-sm tracking-widest text-black bg-[#00FF41] hover:bg-[#00FF41] disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 neon-border font-bold"
      >
        {loading ? "UPLOADING..." : "&gt;&gt; ANALYZE VIDEO"}
      </button>

      <button
        onClick={() => navigate("/history")}
        className="mt-3 w-full py-3 rounded-lg font-mono text-xs tracking-widest text-gray-500 border border-gray-700 hover:text-[#00FF41] hover:border-[#00FF41] transition-all duration-200"
      >
        &gt;&gt; VIEW HISTORY
      </button>
    </div>
  );
}
