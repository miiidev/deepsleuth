import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getTaskStatus, getOriginalVideoUrl, getReportUrl, getHistoryDetail, type TaskStatus } from "../api/client";
import VideoPlayer from "../components/VideoPlayer";
import ConfidenceGraph from "../components/ConfidenceGraph";
import DisclaimerBanner from "../components/DisclaimerBanner";
import Typewriter from "../components/Typewriter";

const LEVEL_STYLES: Record<string, { dot: string; label: string; text: string }> = {
  none: { dot: "bg-[#00FF41] shadow-[0_0_6px_#00FF41]", label: "NONE", text: "text-[#00FF41]" },
  low: { dot: "bg-[#10B981] shadow-[0_0_6px_#10B981]", label: "LOW", text: "text-[#10B981]" },
  moderate: { dot: "bg-[#F59E0B] shadow-[0_0_6px_#F59E0B]", label: "MOD", text: "text-[#F59E0B]" },
  high: { dot: "bg-[#FF3333] shadow-[0_0_6px_#FF3333]", label: "HIGH", text: "text-[#FF3333]" },
};

const REGION_LABELS: Record<string, string> = {
  eyes: "Eyes", nose: "Nose", mouth: "Mouth", forehead: "Forehead", cheeks: "Cheeks", jawline: "Jawline",
};

function ScoreBar({ label, value, max = 1 }: { label: string; value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = value >= 0.7 ? "#FF3333" : value >= 0.4 ? "#F59E0B" : "#00FF41";
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono text-gray-500 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[#1A1A1A] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color, boxShadow: `0 0 6px ${color}40` }} />
      </div>
      <span className="text-xs font-mono" style={{ color }}>{value.toFixed(3)}</span>
    </div>
  );
}

function RegionBar({ name, value }: { name: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? "#FF3333" : value >= 0.4 ? "#F59E0B" : "#00FF41";
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono text-gray-500 w-20 text-right shrink-0">{REGION_LABELS[name] ?? name}</span>
      <div className="flex-1 h-2 bg-[#1A1A1A] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color, boxShadow: `0 0 4px ${color}40` }} />
      </div>
      <span className="text-xs font-mono text-gray-600 w-10 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

function VerdictCard({ level, summary }: { level: string; summary: string }) {
  const s = LEVEL_STYLES[level] ?? LEVEL_STYLES.none;
  const msg = level === "none"
    ? "No significant anomalies detected"
    : level === "low"
      ? "Minor deviations — consistent with authentic footage"
      : level === "moderate"
        ? "Moderate anomalies detected"
        : "Strong anomalies detected";

  return (
    <div className="cyber-card p-5 h-full flex flex-col">
      <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">VERDICT</div>
      <div className="flex items-center gap-3 mb-3">
        <span className={`w-2.5 h-2.5 rounded-full ${s.dot}`} />
        <span className={`text-sm font-heading tracking-wider ${s.text}`}>{msg}</span>
      </div>
      <p className="text-xs font-mono text-gray-500 leading-relaxed flex-1">{summary}</p>
    </div>
  );
}

function SignalOverviewCard({ spatial, temporal, frequency }: { spatial: number; temporal: number; frequency: number }) {
  return (
    <div className="cyber-card p-5 h-full">
      <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">SIGNAL SCORES</div>
      <div className="space-y-3">
        <ScoreBar label="Spatial (XceptionNet)" value={spatial} />
        <ScoreBar label="Temporal (Blink+Flickering)" value={temporal} />
        <ScoreBar label="Frequency (DCT)" value={frequency} />
      </div>
    </div>
  );
}

function TemporalDetailCard({ blinks_per_min, blink_count, flickering_score, landmark_stability }: {
  blinks_per_min: number; blink_count: number; flickering_score: number; landmark_stability: number;
}) {
  return (
    <div className="cyber-card p-5 h-full">
      <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">TEMPORAL</div>
      <div className="space-y-3 font-mono text-xs">
        <div className="flex justify-between"><span className="text-gray-500">Blink Rate</span><span className="text-gray-300">{blinks_per_min}<span className="text-gray-600"> /min</span></span></div>
        <div className="flex justify-between"><span className="text-gray-500">Blinks</span><span className="text-gray-300">{blink_count}</span></div>
        <div className="flex justify-between"><span className="text-gray-500">Flickering</span><span className="text-gray-300">{flickering_score.toFixed(3)}</span></div>
        <div className="flex justify-between"><span className="text-gray-500">Landmark Stability</span><span className="text-gray-300">{landmark_stability.toFixed(3)}</span></div>
      </div>
    </div>
  );
}

export default function Results() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<TaskStatus | null>(null);

  useEffect(() => {
    if (!taskId) return;
    getTaskStatus(taskId)
      .then(setStatus)
      .catch(() => {
        getHistoryDetail(taskId).then((detail) => {
          setStatus({
            task_id: detail.task_id,
            status: detail.status,
            progress: detail.progress,
            message: detail.message,
            error: detail.error,
            frame_scores: detail.frame_scores,
            frame_face_data: detail.frame_face_data,
            analysis_result: detail.analysis_result,
            created_at: detail.created_at,
            updated_at: detail.updated_at,
          });
        });
      });
  }, [taskId]);

  if (!status || !taskId) {
    return (
      <div className="flex justify-center">
        <div className="w-6 h-6 border-2 border-[#00FF41] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const videoUrl = getOriginalVideoUrl(taskId);
  const reportUrl = getReportUrl(taskId);
  const analysis = status.analysis_result;

  if (!analysis) {
    return (
      <div className="w-full max-w-4xl mx-auto text-center">
        <div className="cyber-card p-10">
          <div className="text-lg mb-2 text-gray-400 font-mono">NO ANALYSIS DATA</div>
          <p className="text-sm text-gray-600 font-mono mb-6">This task may still be processing or has no results.</p>
          <button onClick={() => navigate("/upload")} className="px-6 py-2 border border-gray-700 text-gray-500 font-mono text-xs tracking-widest hover:text-gray-300 transition-colors">&gt;&gt; BACK TO UPLOAD</button>
        </div>
      </div>
    );
  }

  const signals = analysis.signals;
  const level = analysis.suspicion_level ?? "none";
  const hasRegions = Object.keys(signals.spatial.regions).length > 0;

  return (
    <div className="w-full max-w-6xl mx-auto">

      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-heading tracking-wider text-[#00FF41] min-h-[2rem]"><Typewriter text="█ ANALYSIS" /></h1>
        <button
          onClick={() => navigate("/upload")}
          className="text-xs font-mono text-gray-600 hover:text-[#00FF41] transition-colors neon-glow-sm"
        >
          &gt;&gt; NEW SCAN
        </button>
      </div>

      {/* Disclaimer */}
      <DisclaimerBanner />

      {/* Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-6 gap-4">

        {/* Row 1: Verdict + Signal Overview + Temporal */}
        <div className="lg:col-span-2 min-h-[160px]">
          <VerdictCard level={level} summary={analysis.summary} />
        </div>

        <div className="lg:col-span-2 min-h-[160px]">
          <SignalOverviewCard
            spatial={signals.spatial.score}
            temporal={signals.temporal.score}
            frequency={signals.frequency.score}
          />
        </div>

        <div className="lg:col-span-2 min-h-[160px]">
          <TemporalDetailCard
            blinks_per_min={signals.temporal.blinks_per_min}
            blink_count={signals.temporal.blink_count}
            flickering_score={signals.temporal.flickering_score}
            landmark_stability={signals.temporal.landmark_stability}
          />
        </div>

        {/* Row 2: Video Player (full width) */}
        <div className="lg:col-span-6">
          <div className="cyber-card overflow-hidden">
            <VideoPlayer taskId={taskId} videoUrl={videoUrl} frameFaceData={status.frame_face_data} />
          </div>
        </div>

        {/* Row 3: Spatial Detail + Region Heatmap (4 cols) | Frequency (2 cols) */}
        <div className="lg:col-span-4">
          <div className="cyber-card p-5 h-full">
            <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">SPATIAL ANALYSIS</div>
            <p className="text-xs font-mono text-gray-500 leading-relaxed mb-4">{signals.spatial.explanation}</p>
            {hasRegions && (
              <>
                <div className="text-[10px] font-heading tracking-widest text-gray-600 mb-2">/ REGION HEATMAP</div>
                <div className="space-y-1.5">
                  {Object.entries(signals.spatial.regions)
                    .sort(([, a], [, b]) => b - a)
                    .map(([name, value]) => (
                      <RegionBar key={name} name={name} value={value} />
                    ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="cyber-card p-5 h-full">
            <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">FREQUENCY (SPECTRAL)</div>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-lg font-mono font-bold ${
                signals.frequency.score >= 0.7 ? "text-[#FF3333]" : signals.frequency.score >= 0.4 ? "text-[#F59E0B]" : "text-[#00FF41]"
              }`}>
                {signals.frequency.score.toFixed(3)}
              </span>
            </div>
            <p className="text-xs font-mono text-gray-500 leading-relaxed">{signals.frequency.explanation}</p>
          </div>
        </div>

        {/* Row 4: Per-Frame Graph (full width) */}
        <div className="lg:col-span-6">
          <div className="cyber-card p-5">
            <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-4">PER-FRAME ANOMALY SCORE</div>
            <ConfidenceGraph scores={status.frame_scores} />
          </div>
        </div>

        {/* Row 5: Download Actions */}
        <div className="lg:col-span-6">
          <div className="cyber-card p-5">
            <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">ACTIONS</div>
            <div className="flex gap-4">
              <a
                href={videoUrl}
                download
                className="flex-1 text-center py-3 border border-[#00FF41] text-[#00FF41] font-mono text-xs tracking-widest hover:bg-[#00FF41] hover:text-black transition-all duration-200 neon-border"
              >
                &gt;&gt; DOWNLOAD VIDEO
              </a>
              <a
                href={reportUrl}
                download
                className="flex-1 text-center py-3 border border-gray-700 text-gray-400 font-mono text-xs tracking-widest hover:border-[#00FF41] hover:text-[#00FF41] transition-all duration-200"
              >
                &gt;&gt; PDF REPORT
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
