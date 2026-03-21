import React from 'react'
import { useLocation } from 'react-router-dom'
import { format } from 'date-fns'
import AlertBadge from './AlertBadge'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/companies': 'Companies',
  '/alerts': 'Alerts',
  '/reports': 'Reports',
  '/settings': 'Settings',
}

export default function Navbar() {
  const location = useLocation()
  const pathBase = '/' + (location.pathname.split('/')[1] || 'dashboard')
  const title = pageTitles[pathBase] || 'Numbers10 PCMonitor'

  return (
    <header
      className="sticky top-0 z-40 flex items-center justify-between px-6 py-3"
      style={{
        background: 'rgba(0,0,0,0.88)',
        backdropFilter: 'blur(12px)',
        borderBottom: '0.667px solid rgba(45,212,191,0.15)',
      }}
    >
      <h1
        className="text-lg font-heading font-bold"
        style={{ color: 'rgb(224,247,250)' }}
      >
        {title}
      </h1>
      <div className="flex items-center gap-4">
        <AlertBadge />
        <span
          className="text-xs"
          style={{ color: 'rgb(100,116,139)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {format(new Date(), 'HH:mm:ss')}
        </span>
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
          style={{ background: 'rgba(45,212,191,0.15)', color: '#2dd4bf' }}
        >
          JN
        </div>
      </div>
    </header>
  )
}
