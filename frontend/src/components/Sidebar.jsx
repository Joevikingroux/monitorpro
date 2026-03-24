import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Bell, FileText, Settings, Download,
  LogOut, ChevronLeft, ChevronRight,
} from 'lucide-react'
import useAuthStore from '../hooks/useAuth'
import AlertBadge from './AlertBadge'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/companies', label: 'Companies', icon: Building2 },
  { path: '/alerts', label: 'Alerts', icon: Bell, badge: true },
  { path: '/reports', label: 'Reports', icon: FileText },
  { path: '/downloads', label: 'Downloads', icon: Download },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const logout = useAuthStore((s) => s.logout)
  const location = useLocation()

  return (
    <aside
      className="flex flex-col h-screen sticky top-0 transition-all duration-300"
      style={{
        width: collapsed ? 60 : 240,
        background: '#000000',
        borderRight: '0.667px solid rgba(45,212,191,0.15)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center justify-center py-4 px-2" style={{ minHeight: 64 }}>
        <img
          src="/logo.png"
          alt="Numbers10"
          style={{
            width: collapsed ? 36 : 160,
            objectFit: 'contain',
            transition: 'width 0.3s ease',
          }}
        />
      </div>

      {/* Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center mx-auto mb-4 w-6 h-6 rounded"
        style={{ background: 'rgba(45,212,191,0.08)', color: '#2dd4bf' }}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col gap-1 px-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path ||
            (item.path === '/dashboard' && location.pathname === '/')
          const Icon = item.icon

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200"
              style={{
                background: isActive ? 'rgba(45,212,191,0.08)' : 'transparent',
                borderLeft: isActive ? '3px solid #2dd4bf' : '3px solid transparent',
                color: isActive ? '#2dd4bf' : 'rgb(148,163,184)',
              }}
            >
              <Icon size={18} />
              {!collapsed && (
                <span className="text-sm font-body flex-1">{item.label}</span>
              )}
              {!collapsed && item.badge && <AlertBadge />}
            </NavLink>
          )
        })}
      </nav>

      {/* Logout */}
      <div className="p-2 mt-auto" style={{ borderTop: '0.667px solid rgba(45,212,191,0.1)' }}>
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg transition-colors"
          style={{ color: 'rgb(148,163,184)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'rgb(148,163,184)')}
        >
          <LogOut size={18} />
          {!collapsed && <span className="text-sm font-body">Logout</span>}
        </button>
      </div>
    </aside>
  )
}
