import React, { useState } from 'react'
import { Monitor, Wifi, WifiOff, AlertTriangle } from 'lucide-react'
import { useMachines } from '../hooks/useMachines'
import { useCompanies } from '../hooks/useCompanies'
import { useUnresolvedAlerts } from '../hooks/useAlerts'
import MachineCard from '../components/MachineCard'

export default function Dashboard() {
  const [companyFilter, setCompanyFilter] = useState('')
  const { data: machines = [], isLoading } = useMachines(companyFilter || undefined)
  const { data: companies = [] } = useCompanies()
  const { data: alertData } = useUnresolvedAlerts()

  const totalMachines = machines.length
  const onlineCount = machines.filter((m) => m.is_online).length
  const alertCount = alertData?.total || 0

  return (
    <div className="p-6">
      {/* Stats bar */}
      <div className="flex flex-wrap gap-4 mb-6">
        <StatCard icon={Monitor} label="Total Machines" value={totalMachines} color="#2dd4bf" />
        <StatCard icon={Wifi} label="Online" value={onlineCount} color="#2dd4bf" />
        <StatCard icon={WifiOff} label="Offline" value={totalMachines - onlineCount} color="#475569" />
        <StatCard icon={AlertTriangle} label="Active Alerts" value={alertCount} color="#ef4444" />

        {/* Company filter */}
        <div className="ml-auto flex items-center">
          <select
            value={companyFilter}
            onChange={(e) => setCompanyFilter(e.target.value)}
            className="text-sm px-3 py-2 rounded-lg outline-none"
            style={{
              background: 'rgb(5,10,18)',
              border: '0.667px solid rgba(45,212,191,0.15)',
              color: 'rgb(224,247,250)',
              borderRadius: '8px',
            }}
          >
            <option value="">All Companies</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Machine grid */}
      {isLoading ? (
        <div className="text-center py-20" style={{ color: 'rgb(100,116,139)' }}>
          Loading machines...
        </div>
      ) : machines.length === 0 ? (
        <div
          className="text-center py-20 rounded-n10"
          style={{
            background: 'rgba(10,18,32,0.7)',
            border: '0.667px solid rgba(45,212,191,0.15)',
          }}
        >
          <Monitor size={48} style={{ color: 'rgb(100,116,139)', margin: '0 auto 16px' }} />
          <p style={{ color: 'rgb(148,163,184)' }}>No machines registered yet.</p>
          <p className="text-sm mt-2" style={{ color: 'rgb(100,116,139)' }}>
            Add a company and install the probe on client PCs to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {machines.map((machine) => (
            <MachineCard key={machine.id} machine={machine} latestMetric={machine.latest_metric} />
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded-n10"
      style={{
        background: 'rgba(10,18,32,0.7)',
        border: '0.667px solid rgba(45,212,191,0.15)',
      }}
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.15)' }}
      >
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <div
          className="text-xl font-heading font-bold"
          style={{ color: 'rgb(224,247,250)', fontFamily: "'Space Grotesk', sans-serif" }}
        >
          {value}
        </div>
        <div
          className="text-xs uppercase"
          style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em', fontFamily: 'Inter, sans-serif' }}
        >
          {label}
        </div>
      </div>
    </div>
  )
}
