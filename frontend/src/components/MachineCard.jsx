import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Monitor, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import MetricGauge from './MetricGauge'
import { useDeleteMachine } from '../hooks/useMachines'

export default function MachineCard({ machine, latestMetric }) {
  const navigate = useNavigate()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const deleteMachine = useDeleteMachine()
  const isOnline = machine.is_online

  function handleDelete(e) {
    e.stopPropagation()
    if (!confirmDelete) {
      setConfirmDelete(true)
      setTimeout(() => setConfirmDelete(false), 3000)
      return
    }
    deleteMachine.mutate(machine.id)
  }
  const cpu = latestMetric?.cpu_percent || 0
  const ram = latestMetric?.ram_percent || 0

  const diskPercent = latestMetric?.disk_usage?.length
    ? Math.max(...latestMetric.disk_usage.map((d) => d.percent || 0))
    : 0

  const lastSeen = machine.last_seen
    ? formatDistanceToNow(new Date(machine.last_seen), { addSuffix: true })
    : 'Never'

  return (
    <div
      onClick={() => navigate(`/machines/${machine.id}`)}
      className="cursor-pointer transition-all duration-200 hover:scale-[1.02]"
      style={{
        background: 'rgba(10,18,32,0.7)',
        border: '0.667px solid rgb(45,212,191)',
        borderRadius: '12px',
        padding: '16px',
        boxShadow: '0 0 20px rgba(45,212,191,0.05)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="flex items-center justify-center w-8 h-8 rounded-lg"
            style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.15)' }}
          >
            <Monitor size={16} style={{ color: '#2dd4bf' }} />
          </div>
          <div>
            <h3
              className="text-sm font-heading font-bold leading-tight"
              style={{ color: 'rgb(224,247,250)' }}
            >
              {machine.display_name || machine.hostname}
            </h3>
            <span className="text-xs" style={{ color: 'rgb(100,116,139)' }}>
              {machine.os_version?.split(' ').slice(0, 2).join(' ') || 'Unknown OS'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {machine.company_name && (
            <span
              className="text-xs px-2 py-0.5 rounded"
              style={{
                background: '#050a12',
                border: '0.667px solid rgba(45,212,191,0.4)',
                color: '#2dd4bf',
                letterSpacing: '0.1em',
              }}
            >
              {machine.company_name}
            </span>
          )}
          <div
            className={`w-2.5 h-2.5 rounded-full ${isOnline ? 'animate-pulse-dot' : ''}`}
            style={{ background: isOnline ? '#2dd4bf' : '#475569' }}
          />
        </div>
      </div>

      {/* Gauges */}
      <div className="flex justify-around items-center my-3">
        <MetricGauge value={cpu} label="CPU" size={80} />
        <MetricGauge value={ram} label="RAM" size={80} />
      </div>

      {/* Disk bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: 'rgb(100,116,139)' }}>DISK</span>
          <span style={{ color: 'rgb(224,247,250)', fontFamily: "'JetBrains Mono', monospace" }}>
            {diskPercent.toFixed(0)}%
          </span>
        </div>
        <div className="h-1.5 rounded-full" style={{ background: 'rgba(45,212,191,0.15)' }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${diskPercent}%`,
              background: diskPercent >= 80 ? '#ef4444' : diskPercent >= 60 ? '#f59e0b' : '#2dd4bf',
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center mt-3 pt-2" style={{ borderTop: '0.667px solid rgba(45,212,191,0.1)' }}>
        <span
          className="text-xs"
          style={{ color: 'rgb(100,116,139)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {lastSeen}
        </span>
        <div className="flex items-center gap-2">
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              background: isOnline ? 'rgba(45,212,191,0.1)' : 'rgba(71,85,105,0.2)',
              color: isOnline ? '#2dd4bf' : '#475569',
            }}
          >
            {isOnline ? 'Online' : 'Offline'}
          </span>
          <button
            onClick={handleDelete}
            title={confirmDelete ? 'Click again to confirm delete' : 'Delete machine'}
            className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded transition-all"
            style={{
              background: confirmDelete ? 'rgba(239,68,68,0.2)' : 'transparent',
              border: `0.667px solid ${confirmDelete ? '#ef4444' : 'rgba(239,68,68,0.3)'}`,
              color: confirmDelete ? '#ef4444' : 'rgba(239,68,68,0.6)',
              cursor: 'pointer',
            }}
          >
            <Trash2 size={11} />
            {confirmDelete ? 'Confirm' : ''}
          </button>
        </div>
      </div>
    </div>
  )
}
