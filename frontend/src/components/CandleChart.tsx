import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Candle } from "../types";

interface Props {
  candles: Candle[];
}

function formatTime(ms: number): string {
  const d = new Date(ms);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

export default function CandleChart({ candles }: Props) {
  const data = candles.map((c) => ({
    ...c,
    t: formatTime(c.open_time_ms),
    color: c.close >= c.open ? "#22c55e" : "#ef4444",
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        No candle data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
      <ComposedChart data={data}>
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
          formatter={(v: number) => v.toFixed(2)}
        />
        <Bar dataKey="volume" fill="#334155" opacity={0.3} barSize={6} />
        <Line
          type="monotone"
          dataKey="close"
          stroke="#a78bfa"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
