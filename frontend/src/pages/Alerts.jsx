import React, { useState } from 'react'
import { Bell, Plus, Check, AlertTriangle, Info } from 'lucide-react'
import { format } from 'date-fns'
import {
  useAlertRules, useAlertEvents, useUnresolvedAlerts,
  useCreateAlertRule, useUpdateAlertRule, useDeleteAlertRule, useAcknowledgeAlert,
  useDeleteAlertEvent,
} from '../hooks/useAlerts'
import { useMachines } from '../hooks/useMachines'
import { useCompanies } from '../hooks/useCompanies'

const SEVERITY_COLORS = { critical: '#ef4444', warning: '#f59e0b', info: '#2dd4bf' }
const METRICS = ['cpu_percent', 'ram_percent', 'disk_percent', 'cpu_temp_c', 'net_latency_ms', 'gpu_percent', 'gpu_temp_c']
const OPERATORS = [{ value: 'gt', label: '>' }, { value: 'lt', label: '<' }, { value: 'eq', label: '=' }]

export default function Alerts() {
  const [view, setView] = useState('rules')
  const [showModal, setShowModal] = useState(false)
  const { data: rules = [] } = useAlertRules()
  const { data: events = [] } = useAlertEvents()
  const { data: unresolved } = useUnresolvedAlerts()
  const { data: machines = [] } = useMachines()
  const { data: companies = [] } = useCompanies()
  const createRule = useCreateAlertRule()
  const updateRule = useUpdateAlertRule()
  const deleteRule = useDeleteAlertRule()
  const ackAlert = useAcknowledgeAlert()
  const deleteEvent = useDeleteAlertEvent()

  const [form, setForm] = useState({
    name: '', company_id: '', machine_id: '', metric_field: 'cpu_percent',
    operator: 'gt', threshold: 90, duration_seconds: 60, severity: 'warning',
    notify_email: false, notify_telegram: false,
  })

  const handleCreate = async (e) => {
    e.preventDefault()
    const payload = { ...form, company_id: form.company_id || null, machine_id: form.machine_id || null }
    await createRule.mutateAsync(payload)
    setShowModal(false)
    setForm({ name: '', company_id: '', machine_id: '', metric_field: 'cpu_percent', operator: 'gt', threshold: 90, duration_seconds: 60, severity: 'warning', notify_email: false, notify_telegram: false })
  }

  return (
    <div className="p-6">
      {/* Summary */}
      <div className="flex gap-4 mb-6">
        <div className="px-4 py-3 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <span className="text-lg font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>{unresolved?.total || 0}</span>
          <span className="text-xs ml-2 uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Unresolved</span>
        </div>
        <div className="px-4 py-3 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <span className="text-lg font-heading font-bold" style={{ color: '#ef4444' }}>{unresolved?.critical || 0}</span>
          <span className="text-xs ml-2 uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>Critical</span>
        </div>
      </div>

      {/* Tab buttons */}
      <div className="flex gap-2 mb-6">
        {['rules', 'events'].map((v) => (
          <button key={v} onClick={() => setView(v)} className="px-4 py-2 text-sm rounded-lg" style={{
            background: view === v ? 'rgba(45,212,191,0.1)' : 'transparent',
            border: `0.667px solid ${view === v ? 'rgba(45,212,191,0.4)' : 'rgba(45,212,191,0.1)'}`,
            color: view === v ? '#2dd4bf' : 'rgb(148,163,184)',
            letterSpacing: '0.1em', textTransform: 'uppercase',
          }}>
            {v}
          </button>
        ))}
        {view === 'rules' && (
          <button onClick={() => setShowModal(true)} className="ml-auto flex items-center gap-2 px-4 py-2 font-bold text-sm" style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}>
            <Plus size={16} /> New Rule
          </button>
        )}
      </div>

      {/* Rules view */}
      {view === 'rules' && (
        <div className="rounded-n10 overflow-hidden" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '0.667px solid rgba(45,212,191,0.1)' }}>
                {['Name', 'Company', 'Machine', 'Metric', 'Condition', 'Severity', 'Enabled', 'Actions'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="hover:bg-[rgba(45,212,191,0.05)]" style={{ borderBottom: '0.667px solid rgba(45,212,191,0.05)' }}>
                  <td className="px-4 py-2" style={{ color: 'rgb(224,247,250)' }}>{r.name}</td>
                  <td className="px-4 py-2 text-xs" style={{ color: 'rgb(148,163,184)' }}>{r.company_name || 'All'}</td>
                  <td className="px-4 py-2 text-xs" style={{ color: 'rgb(148,163,184)' }}>{r.machine_name || 'All'}</td>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: '#2dd4bf' }}>{r.metric_field}</td>
                  <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgb(224,247,250)' }}>{r.operator === 'gt' ? '>' : r.operator === 'lt' ? '<' : '='} {r.threshold}</td>
                  <td className="px-4 py-2"><span className="text-xs px-2 py-0.5 rounded" style={{ background: `${SEVERITY_COLORS[r.severity]}20`, color: SEVERITY_COLORS[r.severity] }}>{r.severity}</span></td>
                  <td className="px-4 py-2">
                    <button onClick={() => updateRule.mutateAsync({ id: r.id, enabled: !r.enabled })} className="w-8 h-4 rounded-full relative" style={{ background: r.enabled ? '#2dd4bf' : '#475569' }}>
                      <span className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all" style={{ left: r.enabled ? '18px' : '2px' }} />
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => { if (confirm('Delete rule?')) deleteRule.mutateAsync(r.id) }} className="text-xs" style={{ color: '#ef4444' }}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Events view */}
      {view === 'events' && (
        <div className="space-y-3">
          {events.map((e) => (
            <div key={e.id} className="flex items-center gap-4 p-4 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: `0.667px solid ${SEVERITY_COLORS[e.severity] || 'rgba(45,212,191,0.15)'}30` }}>
              <AlertTriangle size={18} style={{ color: SEVERITY_COLORS[e.severity] || '#2dd4bf' }} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm" style={{ color: 'rgb(224,247,250)' }}>{e.rule_name}</span>
                  <span className="text-xs px-2 py-0.5 rounded" style={{ background: `${SEVERITY_COLORS[e.severity]}20`, color: SEVERITY_COLORS[e.severity] }}>{e.severity}</span>
                  {e.resolved_at && <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(45,212,191,0.1)', color: '#2dd4bf' }}>Resolved</span>}
                </div>
                <div className="text-xs mt-1" style={{ color: 'rgb(100,116,139)' }}>
                  {e.machine_name} {e.company_name ? `(${e.company_name})` : ''} — {e.message}
                </div>
                <div className="text-xs mt-1 font-mono" style={{ color: 'rgb(100,116,139)' }}>
                  {e.triggered_at ? format(new Date(e.triggered_at), 'yyyy-MM-dd HH:mm:ss') : ''}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {!e.acknowledged && !e.resolved_at && (
                  <button onClick={() => ackAlert.mutateAsync(e.id)} className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold rounded" style={{ border: '1px solid #2dd4bf', color: '#2dd4bf', background: 'transparent', borderRadius: '8px' }}>
                    <Check size={12} /> Acknowledge
                  </button>
                )}
                <button onClick={() => { if (confirm('Delete this alert event?')) deleteEvent.mutateAsync(e.id) }} className="px-3 py-1.5 text-xs font-bold rounded" style={{ border: '1px solid #ef4444', color: '#ef4444', background: 'transparent', borderRadius: '8px' }}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg p-6" style={{ background: '#0d1520', border: '0.667px solid rgba(45,212,191,0.3)', borderRadius: '12px' }}>
            <h2 className="text-lg font-heading font-bold mb-4" style={{ color: 'rgb(224,247,250)' }}>New Alert Rule</h2>
            <form onSubmit={handleCreate} className="flex flex-col gap-3">
              <input placeholder="Rule Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }} />
              <select value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}>
                <option value="">All Companies</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <select value={form.machine_id} onChange={(e) => setForm({ ...form, machine_id: e.target.value })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}>
                <option value="">All Machines</option>
                {machines.map((m) => <option key={m.id} value={m.id}>{m.hostname}</option>)}
              </select>
              <div className="grid grid-cols-3 gap-2">
                <select value={form.metric_field} onChange={(e) => setForm({ ...form, metric_field: e.target.value })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}>
                  {METRICS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
                <select value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}>
                  {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <input type="number" placeholder="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type="number" placeholder="Duration (seconds)" value={form.duration_seconds} onChange={(e) => setForm({ ...form, duration_seconds: Number(e.target.value) })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }} />
                <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="px-3 py-2 text-sm outline-none" style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="flex gap-4 text-sm" style={{ color: 'rgb(148,163,184)' }}>
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.notify_email} onChange={(e) => setForm({ ...form, notify_email: e.target.checked })} /> Email</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.notify_telegram} onChange={(e) => setForm({ ...form, notify_telegram: e.target.checked })} /> Telegram</label>
              </div>
              <div className="flex gap-2 mt-2">
                <button type="submit" className="flex-1 py-2 font-bold text-sm" style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}>Create Rule</button>
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 text-sm" style={{ border: '1px solid #2dd4bf', color: '#2dd4bf', borderRadius: '8px', background: 'transparent' }}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
