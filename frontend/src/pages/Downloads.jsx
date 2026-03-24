import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, Copy, Check, ChevronDown, RefreshCw, AlertTriangle, LogIn } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import useAuthStore from '../hooks/useAuth'

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

const INSTALL_STEPS = [
  { n: 1, title: 'Download the probe installer', body: 'Click the download button above to get PCMonitorProbe_Setup.exe.' },
  { n: 2, title: 'Get your company seed code', body: 'Log in to this dashboard, go to Downloads, select your company and click Get Setup Details to generate a seed code.' },
  { n: 3, title: 'Copy the config.ini', body: 'Copy the pre-filled config.ini shown on the setup details screen.' },
  {
    n: 4,
    title: 'Place both files on the client PC',
    body: (
      <>
        Put <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>PCMonitorProbe_Setup.exe</code> and{' '}
        <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>config.ini</code> in the same folder, e.g.{' '}
        <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>C:\PCMonitorProbe\</code>
      </>
    ),
  },
  {
    n: 5,
    title: 'Run as Administrator',
    body: (
      <>
        Right-click <code style={{ color: 'rgb(224,247,250)', fontFamily: 'monospace', fontSize: 12 }}>PCMonitorProbe_Setup.exe</code> → Run as administrator. It installs as a Windows Service and registers within 30 seconds.
      </>
    ),
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
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold"
      style={{
        background: copied ? 'rgba(45,212,191,0.15)' : 'rgba(45,212,191,0.08)',
        border: '0.667px solid rgba(45,212,191,0.3)',
        borderRadius: '6px',
        color: copied ? '#2dd4bf' : 'rgb(148,163,184)',
      }}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export default function Downloads() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [probeStatus, setProbeStatus] = useState(null)
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [seedCode, setSeedCode] = useState(null)
  const [generating, setGenerating] = useState(false)

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.get('/api/companies/').then((r) => r.data),
    enabled: isAuthenticated,
  })

  const selectedCompany = companies.find((c) => String(c.id) === String(selectedCompanyId))

  const downloadProbe = async () => {
    setProbeStatus('downloading')
    try {
      const headers = {}
      const token = localStorage.getItem('access_token')
      if (token) headers.Authorization = `Bearer ${token}`
      const response = await fetch('/api/downloads/probe', { headers })
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

  const configPreview = seedCode
    ? `[server]\nurl = ${SERVER_URL}\ncompany_token = ${seedCode}\napi_key =\ningest_interval_seconds = 30\nverify_ssl = true\n\n[alerts]\nlocal_alert_log = true\n\n[hardware]\nuse_open_hardware_monitor = false`
    : null

  return (
    <div
      className="min-h-screen"
      style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.05) 0%, #000 50%)' }}
    >
      {/* Top bar */}
      <div
        className="flex items-center justify-between px-8 py-4"
        style={{
          background: 'rgba(0,0,0,0.88)',
          backdropFilter: 'blur(12px)',
          borderBottom: '0.667px solid rgba(45,212,191,0.15)',
        }}
      >
        <img src="/logo.png" alt="Numbers10" style={{ width: 140, objectFit: 'contain' }} />
        {isAuthenticated ? (
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-4 py-2 text-sm"
            style={{ color: '#2dd4bf', textDecoration: 'none', border: '0.667px solid rgba(45,212,191,0.3)', borderRadius: '8px' }}
          >
            ← Dashboard
          </Link>
        ) : (
          <Link
            to="/login"
            className="flex items-center gap-2 px-4 py-2 text-sm font-bold"
            style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px', textDecoration: 'none' }}
          >
            <LogIn size={15} /> Admin Login
          </Link>
        )}
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="mb-8">
          <span
            style={{
              background: '#050a12',
              border: '0.667px solid rgba(45,212,191,0.4)',
              color: '#2dd4bf',
              letterSpacing: '0.15em',
              borderRadius: '6px',
              padding: '4px 14px',
              fontSize: '11px',
            }}
          >
            DOWNLOADS
          </span>
          <h1 className="mt-3 text-2xl font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>
            Probe Installer
          </h1>
          <p className="text-sm mt-1" style={{ color: 'rgb(148,163,184)' }}>
            Download the Windows monitoring agent and install it on any client PC.
          </p>
        </div>

        {/* Download card */}
        <div className="p-6 mb-4" style={cardStyle}>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: 'rgb(224,247,250)' }}>PCMonitorProbe_Setup.exe</p>
              <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>
                Windows Service — collects system metrics and reports to the dashboard every 30 seconds.
              </p>
            </div>
            <button
              onClick={downloadProbe}
              disabled={probeStatus === 'downloading'}
              className="flex items-center gap-2 px-5 py-2.5 font-bold text-sm flex-shrink-0"
              style={{
                background: '#2dd4bf',
                color: '#000',
                borderRadius: '8px',
                opacity: probeStatus === 'downloading' ? 0.6 : 1,
                cursor: probeStatus === 'downloading' ? 'wait' : 'pointer',
              }}
            >
              <Download size={16} />
              {probeStatus === 'downloading' ? 'Downloading…' : 'Download .exe'}
            </button>
          </div>

          {probeStatus === 'missing' && (
            <div className="flex items-start gap-2 p-3 mt-4 rounded-lg text-xs" style={{ background: 'rgba(245,158,11,0.08)', border: '0.667px solid rgba(245,158,11,0.3)', color: 'rgb(245,158,11)' }}>
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              Installer not yet available on the server. Contact your administrator.
            </div>
          )}
          {probeStatus === 'error' && (
            <div className="flex items-center gap-2 p-3 mt-4 rounded-lg text-xs" style={{ background: 'rgba(239,68,68,0.08)', border: '0.667px solid rgba(239,68,68,0.3)', color: '#ef4444' }}>
              <AlertTriangle size={14} /> Download failed — please try again.
            </div>
          )}
          {probeStatus === 'done' && (
            <div className="flex items-center gap-2 p-3 mt-4 rounded-lg text-xs" style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.3)', color: '#2dd4bf' }}>
              <Check size={14} /> Download started — check your browser downloads.
            </div>
          )}
        </div>

        {/* Seed code — logged-in admins only */}
        {isAuthenticated ? (
          <div className="p-6 mb-4" style={cardStyle}>
            <p className="text-xs uppercase tracking-wider mb-1" style={{ color: 'rgb(100,116,139)' }}>Company Seed Code</p>
            <p className="text-xs mb-4" style={{ color: 'rgb(148,163,184)' }}>
              Select a company to generate its registration seed code, then paste it into <code className="font-mono" style={{ fontSize: 11 }}>config.ini</code>.
            </p>

            <div className="flex items-center gap-3 flex-wrap mb-4">
              <div className="relative">
                <select
                  value={selectedCompanyId}
                  onChange={(e) => { setSelectedCompanyId(e.target.value); setSeedCode(null) }}
                  className="w-60 px-3 py-2.5 text-sm outline-none pr-8 appearance-none"
                  style={inputStyle}
                >
                  <option value="">Select a company…</option>
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'rgb(100,116,139)' }} />
              </div>
              <button
                onClick={generateSeed}
                disabled={!selectedCompanyId || generating}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold"
                style={{
                  background: '#2dd4bf', color: '#000', borderRadius: '8px',
                  opacity: !selectedCompanyId ? 0.4 : 1,
                  cursor: !selectedCompanyId ? 'not-allowed' : 'pointer',
                }}
              >
                <RefreshCw size={14} className={generating ? 'animate-spin' : ''} />
                {generating ? 'Generating…' : seedCode ? 'Regenerate' : 'Get Seed Code'}
              </button>
            </div>

            {seedCode && selectedCompany && (
              <>
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>
                      Seed code for <span style={{ color: '#2dd4bf' }}>{selectedCompany.name}</span>
                    </p>
                    <CopyButton text={seedCode} />
                  </div>
                  <div
                    className="px-4 py-3 font-mono text-sm break-all select-all"
                    style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.2)', color: '#2dd4bf', borderRadius: '8px' }}
                  >
                    {seedCode}
                  </div>
                  <p className="flex items-center gap-1.5 mt-2 text-xs" style={{ color: 'rgb(100,116,139)' }}>
                    <AlertTriangle size={12} style={{ color: '#f59e0b' }} />
                    A new seed invalidates the previous one for new registrations. Existing probes are unaffected.
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>config.ini — copy this file to the same folder as the installer</p>
                    <CopyButton text={configPreview} />
                  </div>
                  <pre
                    className="text-xs font-mono p-4 overflow-x-auto"
                    style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', color: 'rgb(224,247,250)', lineHeight: 1.7, borderRadius: '8px' }}
                  >
                    {configPreview}
                  </pre>
                </div>
              </>
            )}
          </div>
        ) : (
          <div
            className="p-5 mb-4 flex items-center justify-between gap-4 flex-wrap"
            style={{ ...cardStyle, border: '0.667px solid rgba(45,212,191,0.1)' }}
          >
            <div>
              <p className="text-sm font-semibold mb-0.5" style={{ color: 'rgb(224,247,250)' }}>Need a company seed code?</p>
              <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>Log in to the admin dashboard to generate a seed code for your company.</p>
            </div>
            <Link
              to="/login"
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold flex-shrink-0"
              style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px', textDecoration: 'none' }}
            >
              <LogIn size={15} /> Admin Login
            </Link>
          </div>
        )}

        {/* Install steps */}
        <div className="p-6" style={cardStyle}>
          <p className="text-xs uppercase tracking-wider mb-5" style={{ color: 'rgb(100,116,139)' }}>Installation Guide</p>
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
      </div>
    </div>
  )
}
