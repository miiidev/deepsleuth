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
        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F1F" />
        <XAxis
          dataKey="frame"
          stroke="#4B5563"
          tick={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}
          label={{ value: "Frame", position: "insideBottomRight", offset: -5, fill: "#4B5563", style: { fontFamily: "JetBrains Mono, monospace" } }}
        />
        <YAxis
          domain={[0, 1]}
          stroke="#4B5563"
          tick={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}
          label={{ value: "Anomaly Score", angle: -90, position: "insideLeft", fill: "#4B5563", style: { fontFamily: "JetBrains Mono, monospace" } }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#111", border: "1px solid #1F1F1F", borderRadius: 12, fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}
          labelStyle={{ color: "#9CA3AF" }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#00FF41"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="score"
          data={[{ frame: 0, score: 0.5 }, { frame: data.length - 1, score: 0.5 }]}
          stroke="#FF3333"
          strokeWidth={1}
          strokeDasharray="4 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
