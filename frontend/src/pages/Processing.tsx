import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getTaskStatus, type TaskStatus } from "../api/client";

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
        <h2 className="text-2xl font-semibold text-red-400 mb-2">Error</h2>
        <p className="text-gray-400">{error}</p>
        <button
          onClick={() => navigate("/")}
          className="mt-6 px-6 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
        >
          Back
        </button>
      </div>
    );
  }

  const pct = status?.progress ?? 0;
  const msg = status?.message ?? "Starting…";

  return (
    <div className="w-full max-w-md mx-auto text-center">
      <h2 className="text-2xl font-semibold mb-2">Analyzing Video</h2>
      <p className="text-gray-500 text-sm mb-8">{msg}</p>

      <div className="w-full bg-gray-800 rounded-full h-3 mb-4 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-purple-600 to-pink-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <p className="text-sm text-gray-400">{pct}%</p>

      <div className="mt-10 flex justify-center">
        <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>

      <button
        onClick={() => navigate("/")}
        className="mt-8 text-sm text-gray-500 hover:text-gray-300 transition-colors"
      >
        Cancel and go back
      </button>
    </div>
  );
}
