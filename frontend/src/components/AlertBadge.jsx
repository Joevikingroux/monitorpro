import React from 'react'
import { useUnresolvedAlerts } from '../hooks/useAlerts'

export default function AlertBadge() {
  const { data } = useUnresolvedAlerts()
  const count = data?.critical || 0

  if (count === 0) return null

  return (
    <span
      className="animate-pulse-badge inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-xs font-bold"
      style={{ background: '#ef4444', color: '#fff' }}
    >
      {count}
    </span>
  )
}
