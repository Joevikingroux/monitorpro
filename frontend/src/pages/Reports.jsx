import React, { useState } from 'react'
import { FileText, Download } from 'lucide-react'
import { useMachines } from '../hooks/useMachines'

export default function Reports() {
  const { data: machines = [] } = useMachines()
  const [machineId, setMachineId] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const downloadMetrics = () => {
    if (!machineId) return alert('Select a machine')
    let url = `/api/reports/machine/${machineId}?`
    if (fromDate) url += `from=${new Date(fromDate).toISOString()}&`
    if (toDate) url += `to=${new Date(toDate).toISOString()}&`
    const token = localStorage.getItem('access_token')
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `machine_${machineId}_metrics.csv`
        a.click()
      })
  }

  const downloadAlerts = () => {
    let url = `/api/reports/alerts?`
    if (fromDate) url += `from=${new Date(fromDate).toISOString()}&`
    if (toDate) url += `to=${new Date(toDate).toISOString()}&`
    const token = localStorage.getItem('access_token')
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = 'alert_events.csv'
        a.click()
      })
  }

  const inputStyle = {
    background: 'rgb(5,10,18)',
    border: '0.667px solid rgba(45,212,191,0.15)',
    borderRadius: '8px',
    color: 'rgb(224,247,250)',
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <img src="/logo.png" alt="Numbers10" style={{ width: 120 }} />
        <div>
          <span className="inline-block text-xs px-3 py-1 rounded mb-1" style={{ background: '#050a12', border: '0.667px solid rgba(45,212,191,0.4)', color: '#2dd4bf', letterSpacing: '0.15em' }}>
            REPORTS
          </span>
        </div>
      </div>

      <div className="max-w-2xl p-6 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>Machine</label>
            <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="w-full px-3 py-2 text-sm outline-none" style={inputStyle}>
              <option value="">Select machine...</option>
              {machines.map((m) => <option key={m.id} value={m.id}>{m.hostname}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>From</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="w-full px-3 py-2 text-sm outline-none" style={inputStyle} />
          </div>
          <div>
            <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>To</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="w-full px-3 py-2 text-sm outline-none" style={inputStyle} />
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={downloadMetrics} className="flex items-center gap-2 px-4 py-2.5 font-bold text-sm" style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}>
            <Download size={16} /> Download Metrics CSV
          </button>
          <button onClick={downloadAlerts} className="flex items-center gap-2 px-4 py-2.5 text-sm" style={{ border: '1px solid #2dd4bf', color: '#2dd4bf', borderRadius: '8px', background: 'transparent' }}>
            <Download size={16} /> Download Alerts CSV
          </button>
        </div>
      </div>
    </div>
  )
}
