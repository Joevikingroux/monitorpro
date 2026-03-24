import React, { useState } from 'react'
import { Download, Copy, Check, ChevronDown, RefreshCw, AlertTriangle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

const SERVER_URL = 'https://monitor.numbers10.co.za'

const cardStyle = {
  background: 'rgba(10,18,32,0.7)',
  border: '0.667px solid rgba(45,212,191,0.15)',
  borderRadius: '12px',
}

const inputStyle = {
  background: 'rgb(5,10,18)',
  border: '0.667px solid rgba(45,212,191,0.15)',
  borderRadius: '8px',
  color: 'rgb(224,247,250)',
}

const pillStyle = {
  background: '#050a12',
  border: '0.667px solid rgba(45,212,191,0.4)',
  color: '#2dd4bf',
  letterSpacing: '0.15em',
  borderRadius: '6px',
  padding: '4px 14px',
  fontSize: '11px',
  display: 'inline-block',
}

const INSTALL_STEPS = [
  {
    n: 1,
    title: 'Download the probe installer',
    body: 'Click the download button below to get PCMonitorProbe_Setup.exe.',
  },
  {
    n: 2,
    title: 'Copy your seed code',
    body: 'Use the copy button above to copy the seed code for this company.',
  },
  {
    n: 3,
    title: 'Place both files on the client PC',
    body: (
      <>
        Copy <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>PCMonitorProbe_Setup.exe</code> and a{' '}
        <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>config.ini</code> file into the same folder (e.g.{' '}
        <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>C:\PCMonitorProbe\</code>).
      </>
    ),
  },
  {
    n: 4,
    title: 'Edit config.ini',
    body: (
      <>
        Open <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>config.ini</code> and paste the seed code as the{' '}
        <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>company_token</code> value (shown below).
      </>
    ),
  },
  {
    n: 5,
    title: 'Run as Administrator',
    body: (
      <>
        Right-click <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>PCMonitorProbe_Setup.exe</code> → Run as administrator. The probe installs as a Windows Service and registers automatically within 30 seconds.
      </>
    ),
  },
  {
    n: 6,
    title: 'Verify in dashboard',
    body: 'The machine appears under this company in the dashboard once the probe connects.',
  },
]

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-all"
      style={{
        background: copied ? 'rgba(45,212,191,0.15)' : 'rgba(45,212,191,0.08)',
        border: '0.667px solid rgba(45,212,191,0.3)',
        borderRadius: '6px',
        color: copied ? '#2dd4bf' : 'rgb(148,163,184)',
        whiteSpace: 'nowrap',
      }}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export default function Downloads() {
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [seedCode, setSeedCode] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [probeStatus, setProbeStatus] = useState(null)

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.get('/api/companies/').then((r) => r.data),
  })

  const selectedCompany = companies.find((c) => String(c.id) === String(selectedCompanyId))

  const generateSeed = async () => {
    if (!selectedCompanyId) return
    setGenerating(true)
    setSeedCode(null)
    try {
      const res = await api.post(`/api/companies/${selectedCompanyId}/token`)
      setSeedCode(res.data.token)
    } finally {
      setGenerating(false)
    }
  }

  const handleCompanyChange = (e) => {
    setSelectedCompanyId(e.target.value)
    setSeedCode(null)
    setProbeStatus(null)
  }

  const downloadProbe = async () => {
    setProbeStatus('downloading')
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/downloads/probe', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.status === 404) { setProbeStatus('missing'); return }
      if (!response.ok) throw new Error()
      const blob = await response.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'PCMonitorProbe_Setup.exe'
      a.click()
      setProbeStatus('done')
    } catch {
      setProbeStatus('error')
    }
  }

  const configPreview = seedCode
    ? `[server]\nurl = ${SERVER_URL}\ncompany_token = ${seedCode}\napi_key =\ningest_interval_seconds = 30\nverify_ssl = true\n\n[alerts]\nlocal_alert_log = true\n\n[hardware]\nuse_open_hardware_monitor = false`
    : null

  return (
    <div className="p-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <img src="/logo.png" alt="Numbers10" style={{ width: 120 }} />
        <span style={pillStyle}>DOWNLOADS</span>
      </div>

      {/* Probe download — always visible */}
      <div className="p-6 mb-4" style={cardStyle}>
        <p className="text-xs uppercase tracking-wider mb-1" style={{ color: 'rgb(100,116,139)' }}>
          Probe Installer
        </p>
        <p className="text-xs mb-4" style={{ color: 'rgb(148,163,184)' }}>
          Windows Service that collects metrics and reports to this dashboard. Run as Administrator on each client PC.
        </p>

        {probeStatus === 'missing' && (
          <div className="flex items-start gap-2 p-3 mb-4 rounded-lg text-xs" style={{ background: 'rgba(245,158,11,0.08)', border: '0.667px solid rgba(245,158,11,0.3)', color: 'rgb(245,158,11)' }}>
            <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
            <span>Installer not found on server. Place the <code className="font-mono" style={{ color: 'rgb(224,247,250)' }}>.exe</code> into the <code className="font-mono" style={{ color: 'rgb(224,247,250)' }}>downloads/</code> folder at the repo root.</span>
          </div>
        )}
        {probeStatus === 'error' && (
          <div className="flex items-center gap-2 p-3 mb-4 rounded-lg text-xs" style={{ background: 'rgba(239,68,68,0.08)', border: '0.667px solid rgba(239,68,68,0.3)', color: '#ef4444' }}>
            <AlertTriangle size={14} /> Download failed — please try again.
          </div>
        )}
        {probeStatus === 'done' && (
          <div className="flex items-center gap-2 p-3 mb-4 rounded-lg text-xs" style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.3)', color: '#2dd4bf' }}>
            <Check size={14} /> Download started — check your browser downloads.
          </div>
        )}

        <button
          onClick={downloadProbe}
          disabled={probeStatus === 'downloading'}
          className="flex items-center gap-2 px-5 py-2.5 font-bold text-sm"
          style={{
            background: '#2dd4bf',
            color: '#000',
            borderRadius: '8px',
            opacity: probeStatus === 'downloading' ? 0.6 : 1,
            cursor: probeStatus === 'downloading' ? 'wait' : 'pointer',
          }}
        >
          <Download size={16} />
          {probeStatus === 'downloading' ? 'Downloading…' : 'Download PCMonitorProbe_Setup.exe'}
        </button>
      </div>

      {/* Step 1 — Select company */}
      <div className="p-6 mb-4" style={cardStyle}>
        <p className="text-xs uppercase tracking-wider mb-2" style={{ color: 'rgb(100,116,139)' }}>
          Step 1 — Select Company
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <select
              value={selectedCompanyId}
              onChange={handleCompanyChange}
              className="w-64 px-3 py-2.5 text-sm outline-none pr-8 appearance-none"
              style={inputStyle}
            >
              <option value="">Select a company…</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'rgb(100,116,139)' }} />
          </div>

          <button
            onClick={generateSeed}
            disabled={!selectedCompanyId || generating}
            className="flex items-center gap-2 px-4 py-2.5 font-bold text-sm"
            style={{
              background: '#2dd4bf',
              color: '#000',
              borderRadius: '8px',
              opacity: !selectedCompanyId ? 0.4 : 1,
              cursor: !selectedCompanyId ? 'not-allowed' : 'pointer',
            }}
          >
            <RefreshCw size={15} className={generating ? 'animate-spin' : ''} />
            {generating ? 'Generating…' : seedCode ? 'Regenerate Seed' : 'Get Setup Details'}
          </button>
        </div>
      </div>

      {/* Setup details — shown after seed generated */}
      {seedCode && selectedCompany && (
        <>
          {/* Seed code */}
          <div className="p-6 mb-4" style={{ ...cardStyle, border: '0.667px solid rgba(45,212,191,0.35)' }}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-xs uppercase tracking-wider mb-0.5" style={{ color: 'rgb(100,116,139)' }}>
                  Step 2 — Seed Code
                </p>
                <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>
                  For <span style={{ color: '#2dd4bf' }}>{selectedCompany.name}</span> — paste this into <code className="font-mono" style={{ fontSize: 11 }}>config.ini</code> as <code className="font-mono" style={{ fontSize: 11 }}>company_token</code>
                </p>
              </div>
              <CopyButton text={seedCode} />
            </div>

            <div
              className="px-4 py-3 rounded-lg font-mono text-sm break-all select-all"
              style={{
                background: 'rgb(5,10,18)',
                border: '0.667px solid rgba(45,212,191,0.2)',
                color: '#2dd4bf',
                letterSpacing: '0.05em',
                borderRadius: '8px',
              }}
            >
              {seedCode}
            </div>

            <p className="flex items-center gap-1.5 mt-3 text-xs" style={{ color: 'rgb(100,116,139)' }}>
              <AlertTriangle size={12} style={{ color: '#f59e0b', flexShrink: 0 }} />
              Generating a new seed invalidates the previous one for new registrations. Already-registered probes are unaffected.
            </p>
          </div>

          {/* config.ini preview */}
          <div className="p-6 mb-4" style={cardStyle}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-xs uppercase tracking-wider mb-0.5" style={{ color: 'rgb(100,116,139)' }}>
                  Step 3 — config.ini
                </p>
                <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>
                  Create this file in the same folder as the probe installer.
                </p>
              </div>
              <CopyButton text={configPreview} />
            </div>

            <pre
              className="text-xs font-mono p-4 rounded-lg overflow-x-auto"
              style={{
                background: 'rgb(5,10,18)',
                border: '0.667px solid rgba(45,212,191,0.15)',
                color: 'rgb(224,247,250)',
                lineHeight: 1.7,
                borderRadius: '8px',
              }}
            >
              {configPreview}
            </pre>
          </div>

          {/* Install steps */}
          <div className="p-6" style={cardStyle}>
            <p className="text-xs uppercase tracking-wider mb-5" style={{ color: 'rgb(100,116,139)' }}>
              Installation Guide
            </p>
            <div className="flex flex-col gap-4">
              {INSTALL_STEPS.map((step) => (
                <div key={step.n} className="flex gap-4">
                  <div
                    className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold font-mono"
                    style={{ background: 'rgba(45,212,191,0.1)', border: '0.667px solid rgba(45,212,191,0.3)', color: '#2dd4bf' }}
                  >
                    {step.n}
                  </div>
                  <div>
                    <p className="text-sm font-semibold mb-0.5" style={{ color: 'rgb(224,247,250)' }}>{step.title}</p>
                    <p className="text-sm" style={{ color: 'rgb(148,163,184)' }}>{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
