import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getTaskStatus, getOriginalVideoUrl, getReportUrl, type TaskStatus } from "../api/client";
import VideoPlayer from "../components/VideoPlayer";
import ConfidenceGraph from "../components/ConfidenceGraph";

const LEVEL_STYLES: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  none: { bg: "bg-teal-950/40", border: "border-teal-700", text: "text-teal-300", dot: "bg-teal-400" },
  low: { bg: "bg-teal-950/40", border: "border-teal-700", text: "text-teal-300", dot: "bg-teal-400" },
  moderate: { bg: "bg-amber-950/40", border: "border-amber-700", text: "text-amber-300", dot: "bg-amber-400" },
  high: { bg: "bg-red-950/40", border: "border-red-700", text: "text-red-300", dot: "bg-red-400" },
};

const REGION_LABELS: Record<string, string> = {
  eyes: "Eyes",
  nose: "Nose",
  mouth: "Mouth",
  forehead: "Forehead",
  cheeks: "Cheeks",
  jawline: "Jawline",
};

function SignalCard({
  title,
  score,
  explanation,
  color,
}: {
  title: string;
  score: number;
  explanation: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-200">{title}</span>
        <span className={`font-mono text-sm ${color}`}>{score.toFixed(3)}</span>
      </div>
      <p className="text-sm text-gray-400 leading-relaxed">{explanation}</p>
    </div>
  );
}

function RegionBar({ name, value }: { name: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.7 ? "bg-red-500" : value >= 0.4 ? "bg-amber-500" : value >= 0.2 ? "bg-yellow-600" : "bg-teal-600";
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-20 text-gray-400 text-right shrink-0">{REGION_LABELS[name] ?? name}</span>
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-gray-500 font-mono text-xs">{value.toFixed(2)}</span>
    </div>
  );
}

export default function Results() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<TaskStatus | null>(null);

  useEffect(() => {
    if (!taskId) return;
    getTaskStatus(taskId).then(setStatus);
  }, [taskId]);

  if (!status || !taskId) {
    return (
      <div className="flex justify-center">
        <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const videoUrl = getOriginalVideoUrl(taskId);
  const reportUrl = getReportUrl(taskId);
  const analysis = status.analysis_result;
  const level = analysis?.suspicion_level ?? "none";
  const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.none;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Analysis Results</h2>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          New analysis
        </button>
      </div>

      {analysis && (
        <div className={`${style.bg} border ${style.border} rounded-xl p-5`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`${style.dot} w-3 h-3 rounded-full shrink-0`} />
            <span className={`${style.text} font-semibold text-lg`}>
              {level === "none"
                ? "No significant anomalies detected"
                : level === "low"
                  ? "Minor deviations — consistent with authentic footage"
                  : level === "moderate"
                    ? "Moderate anomalies detected"
                    : "Strong anomalies detected"}
            </span>
          </div>
          <p className="text-gray-400 text-sm ml-6">{analysis.summary}</p>
        </div>
      )}

      <VideoPlayer taskId={taskId} videoUrl={videoUrl} frameFaceData={status.frame_face_data} />

      {analysis?.signals && (
        <div className="space-y-6">
          <h3 className="text-lg font-medium">Detailed Breakdown</h3>

          <SignalCard
            title="Spatial (XceptionNet)"
            score={analysis.signals.spatial.score}
            explanation={analysis.signals.spatial.explanation}
            color={
              analysis.signals.spatial.score >= 0.5
                ? "text-amber-400"
                : "text-teal-400"
            }
          />

          {Object.keys(analysis.signals.spatial.regions).length > 0 && (
            <div className="bg-gray-900 rounded-xl p-5">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Region Heatmap</h4>
              <div className="space-y-2">
                {Object.entries(analysis.signals.spatial.regions)
                  .sort(([, a], [, b]) => b - a)
                  .map(([name, value]) => (
                    <RegionBar key={name} name={name} value={value} />
                  ))}
              </div>
            </div>
          )}

          <SignalCard
            title="Temporal (Blink + Pose)"
            score={analysis.signals.temporal.score}
            explanation={analysis.signals.temporal.explanation}
            color={
              analysis.signals.temporal.score >= 0.5
                ? "text-amber-400"
                : "text-teal-400"
            }
          />

          <div className="bg-gray-900 rounded-xl p-5 grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Blink Rate</p>
              <p className="text-gray-300 font-mono">
                {analysis.signals.temporal.blinks_per_min}
                <span className="text-gray-600"> /min</span>
              </p>
            </div>
            <div>
              <p className="text-gray-500">Blinks Detected</p>
              <p className="text-gray-300 font-mono">{analysis.signals.temporal.blink_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Head Stability</p>
              <p className="text-gray-300 font-mono">
                {(
                  analysis.signals.temporal.yaw_var +
                  analysis.signals.temporal.pitch_var +
                  analysis.signals.temporal.roll_var
                ).toFixed(1)}
                <span className="text-gray-600"> deg²</span>
              </p>
            </div>
          </div>

          <SignalCard
            title="Frequency (DCT)"
            score={analysis.signals.frequency.score}
            explanation={analysis.signals.frequency.explanation}
            color={
              analysis.signals.frequency.score >= 0.5
                ? "text-amber-400"
                : "text-teal-400"
            }
          />
        </div>
      )}

      <div className="bg-gray-900 rounded-xl p-6">
        <h3 className="text-lg font-medium mb-4">Per-Frame Anomaly Score</h3>
        <ConfidenceGraph scores={status.frame_scores} />
      </div>

      <div className="flex gap-4">
        <a
          href={videoUrl}
          download
          className="flex-1 text-center py-3 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors font-medium"
        >
          Download Video
        </a>
        <a
          href={reportUrl}
          download
          className="flex-1 text-center py-3 rounded-lg bg-purple-600 hover:bg-purple-700 transition-colors font-medium"
        >
          Download PDF Report
        </a>
      </div>
    </div>
  );
}
