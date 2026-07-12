import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Props {
  scores: number[];
}

export default function ConfidenceGraph({ scores }: Props) {
  const data = scores.map((s, i) => ({ frame: i, score: s }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="frame"
          stroke="#6b7280"
          tick={{ fontSize: 12 }}
          label={{ value: "Frame", position: "insideBottomRight", offset: -5, fill: "#6b7280" }}
        />
        <YAxis
          domain={[0, 1]}
          stroke="#6b7280"
          tick={{ fontSize: 12 }}
          label={{ value: "Anomaly Score", angle: -90, position: "insideLeft", fill: "#6b7280" }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#9ca3af" }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#a855f7"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="score"
          data={[{ frame: 0, score: 0.5 }, { frame: data.length - 1, score: 0.5 }]}
          stroke="#d97706"
          strokeWidth={1}
          strokeDasharray="4 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
