import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { IndicatorPoint } from "../types";

interface Props {
  points: IndicatorPoint[];
  color?: string;
}

function formatTime(ms: number): string {
  const d = new Date(ms);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

export default function IndicatorChart({
  points,
  color = "#a78bfa",
}: Props) {
  const data = points.map((p) => ({
    t: formatTime(p.time_ms),
    value: p.value,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-gray-500">
        No indicator data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="t" stroke="#94a3b8" tick={{ fontSize: 11 }} />
        <YAxis
          domain={["auto", "auto"]}
          stroke="#94a3b8"
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => v.toFixed(2)}
        />
        <Tooltip
          contentStyle={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: "#94a3b8" }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
