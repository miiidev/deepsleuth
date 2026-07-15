import { getReportUrl } from "../api/client";

interface Props {
  taskId: string;
  scores: { spatial: number; frequency: number; temporal: number; fused: number };
}

export default function ReportPreview({ taskId, scores }: Props) {
  return (
    <div className="cyber-card p-6 space-y-4">
      <div className="text-[11px] font-heading tracking-widest text-gray-500 mb-3">REPORT SUMMARY</div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        {([
          ["Spatial", scores.spatial],
          ["Frequency", scores.frequency],
          ["Temporal", scores.temporal],
          ["Fused", scores.fused],
        ] as const).map(([label, val]) => (
          <div key={label} className="bg-[#1A1A1A] rounded-lg p-3 border border-[#1F1F1F]">
            <p className="text-[10px] font-mono text-gray-600 tracking-widest">{label}</p>
            <p className="text-lg font-mono font-bold text-[#00FF41] neon-glow-sm">{val.toFixed(3)}</p>
          </div>
        ))}
      </div>
      <a
        href={getReportUrl(taskId)}
        download
        className="block text-center py-3 border border-[#00FF41] text-[#00FF41] font-mono text-xs tracking-widest hover:bg-[#00FF41] hover:text-black transition-all duration-200 neon-border"
      >
        &gt;&gt; DOWNLOAD PDF REPORT
      </a>
    </div>
  );
}
