import React, { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

const TIME_RANGES = [
  { label: '1H', hours: 1 },
  { label: '6H', hours: 6 },
  { label: '24H', hours: 24 },
  { label: '7D', hours: 168 },
]

export default function LiveChart({ data = [], dataKey = 'value', title = '', unit = '%' }) {
  const [range, setRange] = useState('1H')

  const selectedRange = TIME_RANGES.find((r) => r.label === range)
  const cutoff = Date.now() - (selectedRange?.hours || 1) * 3600 * 1000

  const filtered = data.filter((d) => {
    const ts = d.collected_at ? new Date(d.collected_at).getTime() : 0
    return ts >= cutoff
  })

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]
    return (
      <div
        className="rounded-lg p-2 text-xs"
        style={{
          background: 'rgba(10,18,32,0.95)',
          border: '0.667px solid rgba(45,212,191,0.3)',
        }}
      >
        <div style={{ color: 'rgb(224,247,250)', fontFamily: "'JetBrains Mono', monospace" }}>
          {d.value != null ? `${d.value.toFixed(1)}${unit}` : 'N/A'}
        </div>
        <div style={{ color: 'rgb(100,116,139)' }}>
          {d.payload?.collected_at
            ? format(new Date(d.payload.collected_at), 'HH:mm:ss')
            : ''}
        </div>
      </div>
    )
  }

  return (
    <div
      className="rounded-n10 p-4"
      style={{
        background: 'rgba(10,18,32,0.7)',
        border: '0.667px solid rgba(45,212,191,0.15)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-heading font-semibold" style={{ color: 'rgb(224,247,250)' }}>
          {title}
        </h3>
        <div className="flex gap-1">
          {TIME_RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => setRange(r.label)}
              className="px-2 py-0.5 text-xs rounded"
              style={{
                background: range === r.label ? 'rgba(45,212,191,0.15)' : 'transparent',
                border: `0.667px solid ${range === r.label ? 'rgba(45,212,191,0.4)' : 'rgba(45,212,191,0.1)'}`,
                color: range === r.label ? '#2dd4bf' : 'rgb(100,116,139)',
                fontFamily: 'Inter, sans-serif',
                letterSpacing: '0.1em',
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={filtered}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,212,191,0.1)" />
          <XAxis
            dataKey="collected_at"
            tickFormatter={(v) => v ? format(new Date(v), 'HH:mm') : ''}
            stroke="rgb(100,116,139)"
            fontSize={10}
            fontFamily="Inter"
          />
          <YAxis
            stroke="rgb(100,116,139)"
            fontSize={10}
            fontFamily="JetBrains Mono"
            domain={[0, 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke="#2dd4bf"
            strokeWidth={2}
            fill={`url(#grad-${dataKey})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
