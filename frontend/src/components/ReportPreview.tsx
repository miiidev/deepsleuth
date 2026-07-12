import { getReportUrl } from "../api/client";

interface Props {
  taskId: string;
  scores: { spatial: number; frequency: number; temporal: number; fused: number };
}

export default function ReportPreview({ taskId, scores }: Props) {
  return (
    <div className="bg-gray-900 rounded-xl p-6 space-y-4">
      <h3 className="text-lg font-medium">Report Summary</h3>
      <div className="grid grid-cols-2 gap-4 text-sm">
        {[
          ["Spatial", scores.spatial],
          ["Frequency", scores.frequency],
          ["Temporal", scores.temporal],
          ["Fused", scores.fused],
        ].map(([label, val]) => (
          <div key={label as string} className="bg-gray-800 rounded-lg p-3">
            <p className="text-gray-500">{label as string}</p>
            <p className="text-xl font-semibold">{(val as number).toFixed(3)}</p>
          </div>
        ))}
      </div>
      <a
        href={getReportUrl(taskId)}
        download
        className="block text-center py-2 rounded-lg bg-purple-600 hover:bg-purple-700 transition-colors text-sm font-medium"
      >
        Download Full Report (PDF)
      </a>
    </div>
  );
}
