import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Monitor, Cpu, HardDrive, Wifi, Shield, Server, Package, FileWarning, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import { useMachine, useMachineServices, useMachineSoftware, useMachineEventLogs, useDeleteMachine } from '../hooks/useMachines'
import { useLatestMetric, useMetricHistory, useProcesses } from '../hooks/useMetrics'
import MetricGauge from '../components/MetricGauge'
import LiveChart from '../components/LiveChart'

const TABS = ['Overview', 'Processes', 'Services', 'Software', 'Event Logs', 'Security']

export default function MachineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState('Overview')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const deleteMachine = useDeleteMachine()
  const { data: machine } = useMachine(id)
  const { data: latest } = useLatestMetric(id)
  const { data: history = [] } = useMetricHistory(id)
  const { data: procs = [] } = useProcesses(id)
  const { data: svcs = [] } = useMachineServices(id)
  const { data: software = [] } = useMachineSoftware(id)
  const { data: eventLogs = [] } = useMachineEventLogs(id)
  const [softwareSearch, setSoftwareSearch] = useState('')
  const [procSort, setProcSort] = useState('cpu')

  if (!machine) return <div className="p-6" style={{ color: 'rgb(100,116,139)' }}>Loading...</div>

  const diskPercent = latest?.disk_usage?.length
    ? Math.max(...latest.disk_usage.map((d) => d.percent || 0))
    : 0

  return (
    <div className="p-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs mb-4" style={{ color: 'rgb(100,116,139)' }}>
        <Link to="/companies" className="hover:text-n10-teal">Companies</Link>
        <span>/</span>
        <span style={{ color: '#2dd4bf' }}>{machine.company_name || 'Unknown'}</span>
        <span>/</span>
        <span style={{ color: 'rgb(224,247,250)' }}>{machine.hostname}</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-4 mb-6 p-4 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
        <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <Monitor size={24} style={{ color: '#2dd4bf' }} />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>{machine.display_name || machine.hostname}</h2>
          <div className="flex gap-4 text-xs mt-1" style={{ color: 'rgb(100,116,139)' }}>
            <span>{machine.ip_address}</span>
            <span>{machine.os_version}</span>
            <span>{machine.cpu_model}</span>
            <span>{machine.total_ram_gb} GB RAM</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${machine.is_online ? 'animate-pulse-dot' : ''}`} style={{ background: machine.is_online ? '#2dd4bf' : '#475569' }} />
          <button
            onClick={() => {
              if (!confirmDelete) { setConfirmDelete(true); setTimeout(() => setConfirmDelete(false), 3000); return; }
              deleteMachine.mutate(id, { onSuccess: () => navigate('/dashboard') })
            }}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded transition-all"
            style={{
              background: confirmDelete ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.08)',
              border: `1px solid ${confirmDelete ? '#ef4444' : 'rgba(239,68,68,0.4)'}`,
              color: confirmDelete ? '#ef4444' : '#f87171',
              cursor: 'pointer',
              fontWeight: confirmDelete ? 700 : 400,
            }}
          >
            <Trash2 size={14} />
            {confirmDelete ? 'Confirm Delete?' : 'Delete Machine'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-2 text-sm whitespace-nowrap rounded-lg transition-all"
            style={{
              background: tab === t ? 'rgba(45,212,191,0.1)' : 'transparent',
              border: `0.667px solid ${tab === t ? 'rgba(45,212,191,0.4)' : 'rgba(45,212,191,0.1)'}`,
              color: tab === t ? '#2dd4bf' : 'rgb(148,163,184)',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'Overview' && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard label="CPU" value={latest?.cpu_percent} unit="%" />
            <MetricCard label="RAM" value={latest?.ram_percent} unit="%" />
            <MetricCard label="DISK" value={diskPercent} unit="%" />
            <MetricCard label="LATENCY" value={latest?.net_latency_ms} unit="ms" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <LiveChart data={history} dataKey="cpu_percent" title="CPU Usage" unit="%" />
            <LiveChart data={history} dataKey="ram_percent" title="RAM Usage" unit="%" />
            <LiveChart data={history} dataKey="net_sent_mb" title="Network Sent" unit=" MB" />
            <LiveChart data={history} dataKey="net_recv_mb" title="Network Received" unit=" MB" />
          </div>
        </div>
      )}

      {tab === 'Processes' && (
        <div className="rounded-n10 overflow-hidden" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '0.667px solid rgba(45,212,191,0.1)' }}>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>PID</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Name</th>
                <th className="text-left px-4 py-3 text-xs uppercase cursor-pointer" style={{ color: procSort === 'cpu' ? '#2dd4bf' : 'rgb(100,116,139)', letterSpacing: '0.15em' }} onClick={() => setProcSort('cpu')}>CPU%</th>
                <th className="text-left px-4 py-3 text-xs uppercase cursor-pointer" style={{ color: procSort === 'ram' ? '#2dd4bf' : 'rgb(100,116,139)', letterSpacing: '0.15em' }} onClick={() => setProcSort('ram')}>RAM MB</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {[...procs].sort((a, b) => procSort === 'cpu' ? (b.cpu_percent || 0) - (a.cpu_percent || 0) : (b.ram_mb || 0) - (a.ram_mb || 0)).slice(0, 20).map((p, i) => (
                <tr key={i} className="hover:bg-[rgba(45,212,191,0.05)]" style={{ borderBottom: '0.667px solid rgba(45,212,191,0.05)' }}>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(148,163,184)' }}>{p.pid}</td>
                  <td className="px-4 py-2" style={{ color: 'rgb(224,247,250)' }}>{p.name}</td>
                  <td className="px-4 py-2 font-mono" style={{ color: 'rgb(224,247,250)' }}>{p.cpu_percent?.toFixed(1)}</td>
                  <td className="px-4 py-2 font-mono" style={{ color: 'rgb(224,247,250)' }}>{p.ram_mb?.toFixed(0)}</td>
                  <td className="px-4 py-2 text-xs" style={{ color: 'rgb(100,116,139)' }}>{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'Services' && (
        <div className="rounded-n10 overflow-hidden" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '0.667px solid rgba(45,212,191,0.1)' }}>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Service</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Display Name</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Status</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Startup</th>
              </tr>
            </thead>
            <tbody>
              {svcs.map((s, i) => (
                <tr key={i} className="hover:bg-[rgba(45,212,191,0.05)]" style={{ borderBottom: '0.667px solid rgba(45,212,191,0.05)' }}>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(148,163,184)' }}>{s.service_name}</td>
                  <td className="px-4 py-2" style={{ color: 'rgb(224,247,250)' }}>{s.display_name}</td>
                  <td className="px-4 py-2">
                    <span className="text-xs px-2 py-0.5 rounded" style={{
                      background: s.status === 'Running' ? 'rgba(45,212,191,0.1)' : 'rgba(239,68,68,0.1)',
                      color: s.status === 'Running' ? '#2dd4bf' : '#ef4444',
                    }}>{s.status}</span>
                  </td>
                  <td className="px-4 py-2 text-xs" style={{ color: 'rgb(100,116,139)' }}>{s.startup_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'Software' && (
        <div>
          <input
            placeholder="Search software..."
            value={softwareSearch}
            onChange={(e) => setSoftwareSearch(e.target.value)}
            className="mb-4 w-full max-w-md px-3 py-2 text-sm outline-none"
            style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}
          />
          <div className="rounded-n10 overflow-hidden" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '0.667px solid rgba(45,212,191,0.1)' }}>
                  <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Name</th>
                  <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Version</th>
                  <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Publisher</th>
                  <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Install Date</th>
                </tr>
              </thead>
              <tbody>
                {software.filter((s) => !softwareSearch || s.name?.toLowerCase().includes(softwareSearch.toLowerCase())).map((s, i) => (
                  <tr key={i} className="hover:bg-[rgba(45,212,191,0.05)]" style={{ borderBottom: '0.667px solid rgba(45,212,191,0.05)' }}>
                    <td className="px-4 py-2" style={{ color: 'rgb(224,247,250)' }}>{s.name}</td>
                    <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(148,163,184)' }}>{s.version}</td>
                    <td className="px-4 py-2 text-xs" style={{ color: 'rgb(100,116,139)' }}>{s.publisher}</td>
                    <td className="px-4 py-2 text-xs" style={{ color: 'rgb(100,116,139)' }}>{s.install_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'Event Logs' && (
        <div className="rounded-n10 overflow-hidden" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '0.667px solid rgba(45,212,191,0.1)' }}>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Level</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Source</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Event ID</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Message</th>
                <th className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {eventLogs.map((e, i) => (
                <tr key={i} className="hover:bg-[rgba(45,212,191,0.05)]" style={{ borderBottom: '0.667px solid rgba(45,212,191,0.05)' }}>
                  <td className="px-4 py-2">
                    <span className="text-xs px-2 py-0.5 rounded" style={{
                      background: e.level === 'Error' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
                      color: e.level === 'Error' ? '#ef4444' : '#f59e0b',
                    }}>{e.level}</span>
                  </td>
                  <td className="px-4 py-2 text-xs" style={{ color: 'rgb(148,163,184)' }}>{e.log_source}</td>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(148,163,184)' }}>{e.event_id}</td>
                  <td className="px-4 py-2 text-xs max-w-xs truncate" style={{ color: 'rgb(224,247,250)' }}>{e.message}</td>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(100,116,139)' }}>
                    {e.occurred_at ? format(new Date(e.occurred_at), 'yyyy-MM-dd HH:mm') : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'Security' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SecurityCard icon={Shield} label="Firewall" value={latest?.firewall_enabled ? 'ON' : 'Unknown'} color={latest?.firewall_enabled ? '#2dd4bf' : '#475569'} />
          <SecurityCard icon={Shield} label="Antivirus" value="Check logs" color="#2dd4bf" />
          <SecurityCard icon={Package} label="Updates" value="See details" color="#f59e0b" />
          <SecurityCard icon={Server} label="Last Boot" value={machine.last_seen ? format(new Date(machine.last_seen), 'MMM dd HH:mm') : 'Unknown'} color="#2dd4bf" />
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, unit }) {
  return (
    <div className="p-4 rounded-n10 text-center" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
      <div className="text-2xl font-heading font-bold" style={{ color: 'rgb(224,247,250)', fontFamily: "'Space Grotesk', sans-serif" }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{value != null ? Number(value).toFixed(1) : '—'}</span>
        <span className="text-sm ml-1" style={{ color: 'rgb(100,116,139)' }}>{unit}</span>
      </div>
      <div className="text-xs uppercase mt-1" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>{label}</div>
    </div>
  )
}

function SecurityCard({ icon: Icon, label, value, color }) {
  return (
    <div className="p-4 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <Icon size={18} style={{ color }} />
        </div>
        <div>
          <div className="text-sm font-bold" style={{ color: 'rgb(224,247,250)' }}>{value}</div>
          <div className="text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>{label}</div>
        </div>
      </div>
    </div>
  )
}
