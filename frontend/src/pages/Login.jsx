import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../hooks/useAuth'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard')
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        background: 'radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.06) 0%, #000 60%)',
      }}
    >
      <div
        className="w-full max-w-md p-8"
        style={{
          background: 'rgba(10,18,32,0.7)',
          border: '0.667px solid rgba(45,212,191,0.3)',
          borderRadius: '12px',
          boxShadow: '0 0 40px rgba(45,212,191,0.08)',
        }}
      >
        <div className="flex flex-col items-center mb-8">
          <img src="/logo.png" alt="Numbers10" style={{ width: 200 }} className="mb-4" />
          <span
            style={{
              color: '#2dd4bf',
              fontFamily: 'Inter, sans-serif',
              letterSpacing: '0.2em',
              fontSize: '12px',
              textTransform: 'uppercase',
            }}
          >
            TECHNOLOGY SOLUTIONS
          </span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <div
              className="text-sm text-center py-2 rounded-lg"
              style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
            >
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 text-sm outline-none transition-all"
              style={{
                background: 'rgb(5,10,18)',
                border: '0.667px solid rgba(45,212,191,0.15)',
                borderRadius: '8px',
                color: 'rgb(224,247,250)',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#2dd4bf')}
              onBlur={(e) => (e.target.style.borderColor = 'rgba(45,212,191,0.15)')}
              placeholder="admin@numbers10.co.za"
            />
          </div>

          <div>
            <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 text-sm outline-none transition-all"
              style={{
                background: 'rgb(5,10,18)',
                border: '0.667px solid rgba(45,212,191,0.15)',
                borderRadius: '8px',
                color: 'rgb(224,247,250)',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#2dd4bf')}
              onBlur={(e) => (e.target.style.borderColor = 'rgba(45,212,191,0.15)')}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 font-bold text-sm transition-all"
            style={{
              background: '#2dd4bf',
              color: '#000000',
              borderRadius: '8px',
              fontFamily: 'Inter, sans-serif',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.boxShadow = '0 0 20px rgba(45,212,191,0.4)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'none')}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
