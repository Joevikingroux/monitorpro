import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, ChevronDown, AlertTriangle, CheckCircle, LogIn } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import useAuthStore from '../hooks/useAuth'

const cardStyle = {
  background: 'rgba(10,18,32,0.7)',
  border: '0.667px solid rgba(45,212,191,0.15)',
  borderRadius: '12px',
}

const selectStyle = {
  background: 'rgb(5,10,18)',
  border: '0.667px solid rgba(45,212,191,0.15)',
  borderRadius: '8px',
  color: 'rgb(224,247,250)',
}

export default function Downloads() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [status, setStatus] = useState('idle')   // idle | building | done | error | missing
  const [progress, setProgress] = useState(0)
  const [errorMsg, setErrorMsg] = useState('')
  const [cleanStatus, setCleanStatus] = useState('idle') // idle | downloading | done | error

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.get('/api/companies/').then((r) => r.data),
    enabled: isAuthenticated,
  })

  const selectedCompany = companies.find((c) => String(c.id) === String(selectedCompanyId))

  const buildAndDownload = async () => {
    if (!selectedCompanyId) return
    setStatus('building')
    setProgress(0)
    setErrorMsg('')

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`/api/downloads/build/${selectedCompanyId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.status === 404) {
        const data = await response.json().catch(() => ({}))
        setErrorMsg(data.detail || 'Base EXE not found on server.')
        setStatus('missing')
        return
      }
      if (!response.ok) {
        setStatus('error')
        return
      }

      // Stream with real progress
      const contentLength = parseInt(response.headers.get('content-length') || '0', 10)
      const reader = response.body.getReader()
      const chunks = []
      let received = 0

      setStatus('building')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        received += value.length
        if (contentLength > 0) {
          setProgress(Math.min(99, Math.round((received / contentLength) * 100)))
        }
      }

      setProgress(100)

      // Trigger download
      const blob = new Blob(chunks, { type: 'application/octet-stream' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `PCMonitorProbe_${selectedCompany?.slug ?? selectedCompanyId}.exe`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  const reset = () => {
    setStatus('idle')
    setProgress(0)
    setErrorMsg('')
  }

  const downloadClean = async () => {
    setCleanStatus('downloading')
    try {
      const response = await fetch('/api/downloads/probe')
      if (!response.ok) { setCleanStatus('error'); return }
      const blob = await response.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'PCMonitorProbe_Setup.exe'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setCleanStatus('done')
    } catch {
      setCleanStatus('error')
    }
  }

  const isBuilding = status === 'building'

  return (
    <div
      className="min-h-screen"
      style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.05) 0%, #000 55%)' }}
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

      <div className="max-w-xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-8">
          <span style={{
            background: '#050a12',
            border: '0.667px solid rgba(45,212,191,0.4)',
            color: '#2dd4bf',
            letterSpacing: '0.15em',
            borderRadius: '6px',
            padding: '4px 14px',
            fontSize: '11px',
          }}>
            DOWNLOADS
          </span>
          <h1 className="mt-3 text-2xl font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>
            Probe Installer
          </h1>
          <p className="text-sm mt-1" style={{ color: 'rgb(148,163,184)' }}>
            Select a company to build a customised probe installer with the registration token baked in.
          </p>
        </div>

        {/* Clean EXE download — always visible */}
        <div className="p-5 mb-4 flex items-center justify-between gap-4 flex-wrap" style={{ ...cardStyle, border: '0.667px solid rgba(45,212,191,0.1)' }}>
          <div>
            <p className="text-sm font-semibold mb-0.5" style={{ color: 'rgb(224,247,250)' }}>Generic installer (no token)</p>
            <p className="text-xs" style={{ color: 'rgb(148,163,184)' }}>Base EXE — will prompt for company token on first run.</p>
          </div>
          <button
            onClick={downloadClean}
            disabled={cleanStatus === 'downloading'}
            className="flex items-center gap-2 px-4 py-2 text-sm flex-shrink-0"
            style={{
              border: '1px solid rgba(45,212,191,0.4)',
              color: cleanStatus === 'done' ? '#2dd4bf' : 'rgb(148,163,184)',
              borderRadius: '8px',
              background: 'transparent',
              cursor: cleanStatus === 'downloading' ? 'wait' : 'pointer',
            }}
          >
            <Download size={14} />
            {cleanStatus === 'downloading' ? 'Downloading…' : cleanStatus === 'done' ? 'Downloaded' : 'Download'}
          </button>
        </div>

        {isAuthenticated ? (
          <div className="p-6" style={cardStyle}>
            {/* Company selector */}
            <label className="block text-xs uppercase tracking-wider mb-2" style={{ color: 'rgb(100,116,139)' }}>
              Company
            </label>
            <div className="relative mb-5">
              <select
                value={selectedCompanyId}
                onChange={(e) => { setSelectedCompanyId(e.target.value); reset() }}
                disabled={isBuilding}
                className="w-full px-3 py-3 text-sm outline-none pr-8 appearance-none"
                style={{ ...selectStyle, opacity: isBuilding ? 0.5 : 1 }}
              >
                <option value="">Select a company…</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'rgb(100,116,139)' }} />
            </div>

            {/* Progress bar — visible while building or done */}
            {(isBuilding || status === 'done') && (
              <div className="mb-5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs" style={{ color: status === 'done' ? '#2dd4bf' : 'rgb(148,163,184)' }}>
                    {status === 'done' ? `PCMonitorProbe_${selectedCompany?.slug}.zip — ready` : `Building package for ${selectedCompany?.name}…`}
                  </span>
                  <span className="text-xs font-mono" style={{ color: '#2dd4bf' }}>{progress}%</span>
                </div>
                <div style={{ background: 'rgb(5,10,18)', borderRadius: '99px', height: 6, overflow: 'hidden', border: '0.667px solid rgba(45,212,191,0.15)' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${progress}%`,
                      background: status === 'done'
                        ? 'linear-gradient(90deg, #2dd4bf, #14b8a6)'
                        : 'linear-gradient(90deg, #2dd4bf, #14b8a6)',
                      borderRadius: '99px',
                      transition: 'width 0.2s ease',
                      boxShadow: '0 0 8px rgba(45,212,191,0.4)',
                    }}
                  />
                </div>
              </div>
            )}

            {/* Status messages */}
            {status === 'done' && (
              <div className="flex items-center gap-2 p-3 mb-4 rounded-lg text-sm" style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.3)', color: '#2dd4bf' }}>
                <CheckCircle size={15} />
                Download started. Right-click the EXE → Run as Administrator. Installs silently with no prompts.
              </div>
            )}
            {status === 'missing' && (
              <div className="flex items-start gap-2 p-3 mb-4 rounded-lg text-sm" style={{ background: 'rgba(245,158,11,0.08)', border: '0.667px solid rgba(245,158,11,0.3)', color: 'rgb(245,158,11)' }}>
                <AlertTriangle size={15} className="flex-shrink-0 mt-0.5" />
                <span>{errorMsg || 'Base EXE not found. Place PCMonitorProbe_Setup.exe into the downloads/ folder.'}</span>
              </div>
            )}
            {status === 'error' && (
              <div className="flex items-center gap-2 p-3 mb-4 rounded-lg text-sm" style={{ background: 'rgba(239,68,68,0.08)', border: '0.667px solid rgba(239,68,68,0.3)', color: '#ef4444' }}>
                <AlertTriangle size={15} /> Build failed — please try again.
              </div>
            )}

            {/* Action button */}
            <button
              onClick={status === 'done' ? reset : buildAndDownload}
              disabled={!selectedCompanyId || isBuilding}
              className="flex items-center justify-center gap-2 w-full py-3 font-bold text-sm"
              style={{
                background: status === 'done' ? 'transparent' : '#2dd4bf',
                color: status === 'done' ? '#2dd4bf' : '#000',
                border: status === 'done' ? '1px solid #2dd4bf' : 'none',
                borderRadius: '8px',
                opacity: (!selectedCompanyId || isBuilding) ? 0.5 : 1,
                cursor: (!selectedCompanyId || isBuilding) ? 'not-allowed' : 'pointer',
              }}
            >
              <Download size={16} />
              {isBuilding
                ? `Building… ${progress}%`
                : status === 'done'
                  ? 'Build Another'
                  : 'Build & Download'}
            </button>

            {/* Help text */}
            {status === 'idle' && (
              <p className="text-xs mt-4 text-center" style={{ color: 'rgb(100,116,139)' }}>
                Builds a company-specific EXE with the token baked in.
                Run as Administrator — installs silently, no configuration required.
              </p>
            )}
          </div>
        ) : (
          <div className="p-6 text-center" style={cardStyle}>
            <p className="text-sm mb-4" style={{ color: 'rgb(148,163,184)' }}>
              Log in to build a company-specific probe installer.
            </p>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-6 py-3 font-bold text-sm"
              style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px', textDecoration: 'none' }}
            >
              <LogIn size={16} /> Admin Login
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
