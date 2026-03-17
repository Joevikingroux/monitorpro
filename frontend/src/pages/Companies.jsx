import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Plus, Copy, RefreshCw, Monitor, AlertTriangle } from 'lucide-react'
import { useCompanies, useCreateCompany, useRegenerateToken } from '../hooks/useCompanies'

export default function Companies() {
  const { data: companies = [], isLoading } = useCompanies()
  const createCompany = useCreateCompany()
  const regenerateToken = useRegenerateToken()
  const navigate = useNavigate()
  const [showModal, setShowModal] = useState(false)
  const [tokenModal, setTokenModal] = useState(null)
  const [form, setForm] = useState({ name: '', slug: '', contact_name: '', contact_email: '', notes: '' })

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      const data = await createCompany.mutateAsync(form)
      setTokenModal(data.token)
      setShowModal(false)
      setForm({ name: '', slug: '', contact_name: '', contact_email: '', notes: '' })
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create company')
    }
  }

  const handleRegenerate = async (companyId) => {
    if (!confirm('Regenerate token? The old token will be invalidated.')) return
    try {
      const data = await regenerateToken.mutateAsync(companyId)
      setTokenModal(data.token)
    } catch {
      alert('Failed to regenerate token')
    }
  }

  const copyToken = (token) => {
    navigator.clipboard.writeText(token)
    alert('Token copied to clipboard!')
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <span
            className="inline-block text-xs px-3 py-1 rounded mb-2"
            style={{
              background: '#050a12', border: '0.667px solid rgba(45,212,191,0.4)',
              color: '#2dd4bf', letterSpacing: '0.15em', fontFamily: 'Inter, sans-serif',
            }}
          >
            COMPANIES
          </span>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 font-bold text-sm"
          style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}
        >
          <Plus size={16} /> Add Company
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-20" style={{ color: 'rgb(100,116,139)' }}>Loading...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((c) => (
            <div
              key={c.id}
              className="p-5 cursor-pointer transition-all hover:scale-[1.01]"
              style={{
                background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgb(45,212,191)',
                borderRadius: '12px', boxShadow: '0 0 20px rgba(45,212,191,0.05)',
              }}
              onClick={() => navigate(`/dashboard?company=${c.id}`)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ background: 'rgba(45,212,191,0.08)', border: '0.667px solid rgba(45,212,191,0.15)' }}
                  >
                    <Building2 size={18} style={{ color: '#2dd4bf' }} />
                  </div>
                  <div>
                    <h3 className="font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>{c.name}</h3>
                    <span className="text-xs" style={{ color: 'rgb(100,116,139)' }}>{c.slug}</span>
                  </div>
                </div>
                {c.alert_count > 0 && (
                  <span className="flex items-center gap-1 text-xs px-2 py-1 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>
                    <AlertTriangle size={12} /> {c.alert_count}
                  </span>
                )}
              </div>

              <div className="flex gap-4 mb-3">
                <div className="text-center">
                  <div className="text-lg font-heading font-bold" style={{ color: 'rgb(224,247,250)' }}>
                    {c.online_count || 0}/{c.machine_count || 0}
                  </div>
                  <div className="text-xs uppercase" style={{ color: 'rgb(100,116,139)', letterSpacing: '0.15em' }}>
                    ONLINE
                  </div>
                </div>
              </div>

              <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => handleRegenerate(c.id)}
                  className="flex items-center gap-1 text-xs px-3 py-1.5 rounded"
                  style={{ border: '1px solid #2dd4bf', color: '#2dd4bf', background: 'transparent', borderRadius: '8px' }}
                >
                  <RefreshCw size={12} /> Regenerate Token
                </button>
              </div>

              {c.contact_email && (
                <div className="mt-3 text-xs" style={{ color: 'rgb(100,116,139)' }}>
                  {c.contact_name} — {c.contact_email}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-md p-6" style={{ background: '#0d1520', border: '0.667px solid rgba(45,212,191,0.3)', borderRadius: '12px' }}>
            <h2 className="text-lg font-heading font-bold mb-4" style={{ color: 'rgb(224,247,250)' }}>Add Company</h2>
            <form onSubmit={handleCreate} className="flex flex-col gap-3">
              {['name', 'slug', 'contact_name', 'contact_email', 'notes'].map((field) => (
                <input
                  key={field}
                  placeholder={field.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  required={field === 'name' || field === 'slug'}
                  className="px-3 py-2 text-sm outline-none"
                  style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.15)', borderRadius: '8px', color: 'rgb(224,247,250)' }}
                />
              ))}
              <div className="flex gap-2 mt-2">
                <button type="submit" className="flex-1 py-2 font-bold text-sm" style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}>
                  Create
                </button>
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 text-sm" style={{ border: '1px solid #2dd4bf', color: '#2dd4bf', borderRadius: '8px', background: 'transparent' }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Token Display Modal */}
      {tokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-md p-6" style={{ background: '#0d1520', border: '0.667px solid rgba(45,212,191,0.3)', borderRadius: '12px' }}>
            <h2 className="text-lg font-heading font-bold mb-2" style={{ color: 'rgb(224,247,250)' }}>Company Token</h2>
            <p className="text-xs mb-4" style={{ color: '#f59e0b' }}>Save this token — it will not be shown again!</p>
            <div
              className="flex items-center gap-2 p-3 rounded-lg mb-4"
              style={{ background: 'rgb(5,10,18)', border: '0.667px solid rgba(45,212,191,0.3)' }}
            >
              <code className="flex-1 text-xs break-all" style={{ color: '#2dd4bf', fontFamily: "'JetBrains Mono', monospace" }}>
                {tokenModal}
              </code>
              <button onClick={() => copyToken(tokenModal)} style={{ color: '#2dd4bf' }}>
                <Copy size={16} />
              </button>
            </div>
            <button
              onClick={() => setTokenModal(null)}
              className="w-full py-2 font-bold text-sm"
              style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
