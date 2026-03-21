import React, { useState } from 'react'
import { FileText, Download, Calendar } from 'lucide-react'
import { format, subDays, subHours, startOfDay, endOfDay } from 'date-fns'
import { useMachines } from '../hooks/useMachines'

const PRESETS = [
  { label: 'Last 24h',  getDates: () => ({ from: subHours(new Date(), 24), to: new Date() }) },
  { label: 'Last 7d',   getDates: () => ({ from: startOfDay(subDays(new Date(), 7)), to: new Date() }) },
  { label: 'Last 30d',  getDates: () => ({ from: startOfDay(subDays(new Date(), 30)), to: new Date() }) },
  { label: 'Last 90d',  getDates: () => ({ from: startOfDay(subDays(new Date(), 90)), to: new Date() }) },
  { label: 'Custom',    getDates: null },
]

const inputStyle = {
  background: 'rgb(5,10,18)',
  border: '0.667px solid rgba(45,212,191,0.15)',
  borderRadius: '8px',
  color: 'rgb(224,247,250)',
}

export default function Reports() {
  const { data: machines = [] } = useMachines()
  const [machineId, setMachineId] = useState('')
  const [preset, setPreset]       = useState('Last 7d')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo,   setCustomTo]   = useState('')
  const [downloading, setDownloading] = useState(null)
  const [error, setError] = useState('')

  const getDateRange = () => {
    if (preset === 'Custom') {
      return {
        from: customFrom ? new Date(customFrom) : null,
        to:   customTo   ? endOfDay(new Date(customTo)) : null,
      }
    }
    const p = PRESETS.find((p) => p.label === preset)
    return p ? p.getDates() : { from: null, to: null }
  }

  const { from, to } = getDateRange()

  const download = async (type) => {
    if (type === 'metrics' && !machineId) {
      setError('Please select a machine for the Metrics report.')
      return
    }
    setError('')
    setDownloading(type)

    let url = type === 'metrics'
      ? `/api/reports/machine/${machineId}?`
      : `/api/reports/alerts?`

    if (from) url += `from=${from.toISOString()}&`
    if (to)   url += `to=${to.toISOString()}&`

    try {
      const token = localStorage.getItem('access_token')
      const resp  = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!resp.ok) throw new Error(`Server error ${resp.status}`)
      const blob  = await resp.blob()
      const a     = document.createElement('a')
      a.href      = URL.createObjectURL(blob)
      const machine = machines.find((m) => String(m.id) === String(machineId))
      a.download  = type === 'metrics'
        ? `Metrics_${machine?.hostname || machineId}_${format(new Date(), 'yyyyMMdd')}.pdf`
        : `Alerts_${format(new Date(), 'yyyyMMdd')}.pdf`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e) {
      setError(e.message || 'Download failed')
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <img src="/logo.png" alt="Numbers10" style={{ width: 110 }} />
        <div>
          <span className="inline-block text-xs px-3 py-1 rounded mb-1"
            style={{ background: '#050a12', border: '0.667px solid rgba(45,212,191,0.4)', color: '#2dd4bf', letterSpacing: '0.15em' }}>
            REPORTS
          </span>
          <p className="text-xs" style={{ color: 'rgb(100,116,139)' }}>
            Generate PDF reports for metrics and alert events
          </p>
        </div>
      </div>

      <div className="p-6 rounded-n10 space-y-6"
        style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>

        {/* Date range */}
        <div>
          <label className="block text-xs mb-2 uppercase tracking-wider font-bold"
            style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>
            <Calendar size={11} className="inline mr-1" />Date Range
          </label>

          {/* Preset buttons */}
          <div className="flex gap-2 flex-wrap mb-3">
            {PRESETS.map((p) => (
              <button key={p.label} onClick={() => setPreset(p.label)}
                className="px-3 py-1.5 text-xs font-bold rounded-lg transition-all"
                style={{
                  background: preset === p.label ? '#2dd4bf' : 'rgba(45,212,191,0.05)',
                  color:      preset === p.label ? '#000'    : '#2dd4bf',
                  border:     `0.667px solid ${preset === p.label ? '#2dd4bf' : 'rgba(45,212,191,0.2)'}`,
                }}>
                {p.label}
              </button>
            ))}
          </div>

          {/* Custom date pickers */}
          {preset === 'Custom' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs mb-1" style={{ color: 'rgb(100,116,139)' }}>From</label>
                <input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)}
                  className="w-full px-3 py-2 text-sm outline-none"
                  style={{ ...inputStyle, colorScheme: 'dark' }} />
              </div>
              <div>
                <label className="block text-xs mb-1" style={{ color: 'rgb(100,116,139)' }}>To</label>
                <input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)}
                  className="w-full px-3 py-2 text-sm outline-none"
                  style={{ ...inputStyle, colorScheme: 'dark' }} />
              </div>
            </div>
          )}

          {/* Active range display */}
          {(from || to) && (
            <p className="text-xs mt-2 font-mono" style={{ color: '#2dd4bf' }}>
              {from ? format(from, 'yyyy-MM-dd HH:mm') : '—'}  →  {to ? format(to, 'yyyy-MM-dd HH:mm') : 'Now'}
            </p>
          )}
        </div>

        {/* Divider */}
        <div style={{ height: '0.667px', background: 'rgba(45,212,191,0.15)' }} />

        {/* Machine Metrics Report */}
        <div>
          <h3 className="text-sm font-heading font-bold mb-3" style={{ color: 'rgb(224,247,250)' }}>
            Machine Metrics Report
          </h3>
          <p className="text-xs mb-3" style={{ color: 'rgb(100,116,139)' }}>
            CPU, RAM, network and disk metrics for a specific machine. Includes summary stats and full data table.
          </p>
          <div className="flex items-center gap-3">
            <select value={machineId} onChange={(e) => setMachineId(e.target.value)}
              className="flex-1 px-3 py-2 text-sm outline-none"
              style={inputStyle}>
              <option value="">Select machine…</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.hostname} {m.ip_address ? `— ${m.ip_address}` : ''}
                </option>
              ))}
            </select>
            <button onClick={() => download('metrics')} disabled={downloading === 'metrics'}
              className="flex items-center gap-2 px-4 py-2 font-bold text-sm whitespace-nowrap"
              style={{
                background: downloading === 'metrics' ? 'rgba(45,212,191,0.4)' : '#2dd4bf',
                color: '#000', borderRadius: '8px',
              }}>
              <FileText size={15} />
              {downloading === 'metrics' ? 'Generating…' : 'Download PDF'}
            </button>
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: '0.667px', background: 'rgba(45,212,191,0.15)' }} />

        {/* Alerts Report */}
        <div>
          <h3 className="text-sm font-heading font-bold mb-3" style={{ color: 'rgb(224,247,250)' }}>
            Alert Events Report
          </h3>
          <p className="text-xs mb-3" style={{ color: 'rgb(100,116,139)' }}>
            All alert events across all machines. Includes severity breakdown summary and full event list.
          </p>
          <button onClick={() => download('alerts')} disabled={downloading === 'alerts'}
            className="flex items-center gap-2 px-4 py-2 font-bold text-sm"
            style={{
              border: '1px solid #2dd4bf',
              color: downloading === 'alerts' ? 'rgba(45,212,191,0.4)' : '#2dd4bf',
              borderRadius: '8px', background: 'transparent',
            }}>
            <FileText size={15} />
            {downloading === 'alerts' ? 'Generating…' : 'Download Alerts PDF'}
          </button>
        </div>

        {/* Error */}
        {error && (
          <p className="text-sm" style={{ color: '#ef4444' }}>⚠ {error}</p>
        )}
      </div>
    </div>
  )
}
