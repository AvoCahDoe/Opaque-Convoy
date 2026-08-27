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
      <p className="text-xs text-[var(--steel)]">
        Run a plan to load the cost–opacity sweep.
      </p>
    )
  }

  return (
    <div className="h-40 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="rgba(197,208,220,0.12)" strokeDasharray="3 3" />
          <XAxis
            dataKey="fraction"
            tick={{ fill: '#8b9aab', fontSize: 11 }}
            label={{ value: 'Checkpoint density', position: 'insideBottom', offset: -2, fill: '#8b9aab', fontSize: 10 }}
          />
          <YAxis
            tick={{ fill: '#8b9aab', fontSize: 11 }}
            label={{ value: 'Extra cost %', angle: -90, position: 'insideLeft', fill: '#8b9aab', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{
              background: '#12161c',
              border: '1px solid rgba(197,208,220,0.2)',
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
            stroke="#e8a54b"
            strokeWidth={2}
            dot={{ r: 3, fill: '#e8a54b' }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
