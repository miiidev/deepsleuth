import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getTaskStatus, type TaskStatus } from "../api/client";
import Typewriter from "../components/Typewriter";

export default function Processing() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const s = await getTaskStatus(taskId);
        setStatus(s);
        if (s.status === "completed") {
          clearInterval(interval);
          navigate(`/results/${taskId}`);
        }
        if (s.status === "failed") {
          clearInterval(interval);
          setError(s.error || "Processing failed");
        }
      } catch {
        clearInterval(interval);
        setError("Failed to fetch status");
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [taskId, navigate]);

  if (error) {
    return (
      <div className="text-center">
        <h2 className="text-2xl font-heading tracking-wider text-[#FF3333] mb-2 min-h-[2rem]"><Typewriter text="█ ERROR" /></h2>
        <p className="text-gray-500 font-mono text-sm">{error}</p>
        <button
          onClick={() => navigate("/upload")}
          className="mt-6 px-6 py-2 border border-gray-700 text-gray-500 font-mono text-xs tracking-widest hover:text-gray-300 transition-colors"
        >
          &gt;&gt; BACK
        </button>
      </div>
    );
  }

  const pct = status?.progress ?? 0;
  const msg = status?.message ?? "Starting…";

  return (
    <div className="w-full max-w-md mx-auto text-center">
      <h2 className="text-2xl font-heading tracking-wider text-[#00FF41] mb-2 min-h-[2rem]"><Typewriter text="█ PROCESSING" /></h2>
      <p className="text-gray-600 font-mono text-sm mb-8 neon-glow-sm">{msg}</p>

      <div className="w-full bg-[#1A1A1A] rounded-full h-2 mb-4 overflow-hidden border border-[#1F1F1F]">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: "#00FF41", boxShadow: "0 0 8px #00FF4166" }}
        />
      </div>

      <p className="text-sm font-mono text-[#00FF41] neon-glow-sm">{pct}%</p>

      <div className="mt-10 flex justify-center">
        <div className="w-6 h-6 border-2 border-[#00FF41] border-t-transparent rounded-full animate-spin" />
      </div>

      <button
        onClick={() => navigate("/upload")}
        className="mt-8 text-xs font-mono text-gray-600 hover:text-gray-400 transition-colors"
      >
        &gt;&gt; CANCEL
      </button>
    </div>
  );
}
