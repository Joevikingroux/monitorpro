import React from 'react'

export default function MetricGauge({ value = 0, label = '', size = 100 }) {
  const clampedValue = Math.min(100, Math.max(0, value || 0))
  const radius = (size - 12) / 2
  const cx = size / 2
  const cy = size / 2 + 10
  const startAngle = -180
  const endAngle = 0
  const sweepAngle = (clampedValue / 100) * (endAngle - startAngle)

  const toRad = (deg) => (deg * Math.PI) / 180
  const arcX = (angle) => cx + radius * Math.cos(toRad(angle))
  const arcY = (angle) => cy + radius * Math.sin(toRad(angle))

  const bgPath = `M ${arcX(startAngle)} ${arcY(startAngle)} A ${radius} ${radius} 0 1 1 ${arcX(endAngle)} ${arcY(endAngle)}`

  const valAngle = startAngle + sweepAngle
  const largeArc = sweepAngle > 180 ? 1 : 0
  const valPath = clampedValue > 0
    ? `M ${arcX(startAngle)} ${arcY(startAngle)} A ${radius} ${radius} 0 ${largeArc} 1 ${arcX(valAngle)} ${arcY(valAngle)}`
    : ''

  let color = '#2dd4bf'
  if (clampedValue >= 80) color = '#ef4444'
  else if (clampedValue >= 60) color = '#f59e0b'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        <path
          d={bgPath}
          fill="none"
          stroke="rgba(45,212,191,0.15)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        {valPath && (
          <path
            d={valPath}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            style={{ transition: 'all 0.5s ease' }}
          />
        )}
        <text
          x={cx}
          y={cy - 8}
          textAnchor="middle"
          fill="rgb(224,247,250)"
          fontFamily="'JetBrains Mono', monospace"
          fontWeight="bold"
          fontSize={size * 0.22}
        >
          {Math.round(clampedValue)}%
        </text>
      </svg>
      {label && (
        <span
          className="text-xs uppercase tracking-[0.15em] mt-1"
          style={{ color: 'rgb(100,116,139)', fontFamily: 'Inter, sans-serif' }}
        >
          {label}
        </span>
      )}
    </div>
  )
}
