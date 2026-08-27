import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export default function TradeoffChart({ points }) {
  const data = (points || []).map((p) => ({
    fraction: p.checkpoint_fraction,
    overhead: p.overhead_pct ?? null,
    secure: p.secure_found ? 1 : 0,
    checkpoints: p.n_checkpoints,
  }))

  if (!data.length) {
    return (
      <p className="text-xs text-[var(--steel-ink)] m-0">
        Run a plan to load the cost–opacity sweep.
      </p>
    )
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 4 }}>
          <CartesianGrid stroke="rgba(26,31,38,0.08)" strokeDasharray="3 3" />
          <XAxis
            dataKey="fraction"
            tick={{ fill: '#5c6b7a', fontSize: 11 }}
            label={{
              value: 'Checkpoint density',
              position: 'insideBottom',
              offset: -2,
              fill: '#5c6b7a',
              fontSize: 10,
            }}
          />
          <YAxis
            tick={{ fill: '#5c6b7a', fontSize: 11 }}
            label={{
              value: 'Extra cost %',
              angle: -90,
              position: 'insideLeft',
              fill: '#5c6b7a',
              fontSize: 10,
            }}
          />
          <Tooltip
            contentStyle={{
              background: '#f8f9fa',
              border: '1px solid rgba(26,31,38,0.12)',
              color: '#12151a',
              fontSize: 12,
            }}
            formatter={(value, name) => [
              value == null ? '—' : `${Number(value).toFixed(1)}${name === 'overhead' ? '%' : ''}`,
              name === 'overhead' ? 'Overhead' : name,
            ]}
          />
          <Line
            type="monotone"
            dataKey="overhead"
            stroke="#c47a1a"
            strokeWidth={2}
            dot={{ r: 3, fill: '#c47a1a' }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
