import React, { useState } from 'react'
import { Save, Send } from 'lucide-react'
import useAuthStore from '../hooks/useAuth'
import client from '../api/client'

export default function Settings() {
  const changePassword = useAuthStore((s) => s.changePassword)
  const [pw, setPw] = useState({ current: '', new: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState('')
  const [emailTestMsg, setEmailTestMsg] = useState('')
  const [emailTesting, setEmailTesting] = useState(false)
  const [telegramTestMsg, setTelegramTestMsg] = useState('')
  const [telegramTesting, setTelegramTesting] = useState(false)

  const testEmail = async () => {
    setEmailTesting(true)
    setEmailTestMsg('')
    try {
      const { data } = await client.post('/alerts/test/email')
      setEmailTestMsg({ ok: true, text: data.message })
    } catch (e) {
      setEmailTestMsg({ ok: false, text: e.response?.data?.detail || 'Failed' })
    } finally {
      setEmailTesting(false)
    }
  }

  const testTelegram = async () => {
    setTelegramTesting(true)
    setTelegramTestMsg('')
    try {
      const { data } = await client.post('/alerts/test/telegram')
      setTelegramTestMsg({ ok: true, text: data.message })
    } catch (e) {
      setTelegramTestMsg({ ok: false, text: e.response?.data?.detail || 'Failed' })
    } finally {
      setTelegramTesting(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (pw.new !== pw.confirm) return setPwMsg('Passwords do not match')
    try {
      await changePassword(pw.current, pw.new)
      setPwMsg('Password changed successfully')
      setPw({ current: '', new: '', confirm: '' })
    } catch (err) {
      setPwMsg(err.response?.data?.detail || 'Failed to change password')
    }
  }

  const inputStyle = {
    background: 'rgb(5,10,18)',
    border: '0.667px solid rgba(45,212,191,0.15)',
    borderRadius: '8px',
    color: 'rgb(224,247,250)',
  }

  return (
    <div className="p-6 max-w-3xl">
      {/* Change Password */}
      <Section title="Admin Profile">
        <form onSubmit={handlePasswordChange} className="flex flex-col gap-3">
          <input type="password" placeholder="Current Password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} className="px-3 py-2 text-sm outline-none w-full" style={inputStyle} />
          <input type="password" placeholder="New Password" value={pw.new} onChange={(e) => setPw({ ...pw, new: e.target.value })} className="px-3 py-2 text-sm outline-none w-full" style={inputStyle} />
          <input type="password" placeholder="Confirm New Password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} className="px-3 py-2 text-sm outline-none w-full" style={inputStyle} />
          {pwMsg && <p className="text-sm" style={{ color: pwMsg.includes('success') ? '#2dd4bf' : '#ef4444' }}>{pwMsg}</p>}
          <button type="submit" className="flex items-center gap-2 px-4 py-2 font-bold text-sm w-fit" style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px' }}>
            <Save size={14} /> Change Password
          </button>
        </form>
      </Section>

      {/* SMTP */}
      <Section title="Email (SMTP)">
        <p className="text-xs mb-3" style={{ color: 'rgb(100,116,139)' }}>
          Configured via .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, ALERT_EMAIL
        </p>
        <button
          onClick={testEmail}
          disabled={emailTesting}
          className="flex items-center gap-2 px-4 py-2 font-bold text-sm"
          style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px', opacity: emailTesting ? 0.6 : 1 }}
        >
          <Send size={14} /> {emailTesting ? 'Sending…' : 'Send Test Email'}
        </button>
        {emailTestMsg && (
          <p className="text-sm mt-2" style={{ color: emailTestMsg.ok ? '#2dd4bf' : '#ef4444' }}>
            {emailTestMsg.ok ? '✓' : '✗'} {emailTestMsg.text}
          </p>
        )}
      </Section>

      {/* Telegram */}
      <Section title="Telegram">
        <p className="text-xs mb-3" style={{ color: 'rgb(100,116,139)' }}>
          Configured via .env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID. Per-company chat IDs can be set on the Companies page.
        </p>
        <button
          onClick={testTelegram}
          disabled={telegramTesting}
          className="flex items-center gap-2 px-4 py-2 font-bold text-sm"
          style={{ background: '#2dd4bf', color: '#000', borderRadius: '8px', opacity: telegramTesting ? 0.6 : 1 }}
        >
          <Send size={14} /> {telegramTesting ? 'Sending…' : 'Send Test Telegram'}
        </button>
        {telegramTestMsg && (
          <p className="text-sm mt-2" style={{ color: telegramTestMsg.ok ? '#2dd4bf' : '#ef4444' }}>
            {telegramTestMsg.ok ? '✓' : '✗'} {telegramTestMsg.text}
          </p>
        )}
      </Section>

      {/* Retention */}
      <Section title="System">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs mb-1 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>Data Retention (days)</label>
            <input type="number" placeholder="90" disabled className="px-3 py-2 text-sm w-full opacity-50" style={inputStyle} />
          </div>
          <div>
            <label className="block text-xs mb-1 uppercase tracking-wider" style={{ color: 'rgb(100,116,139)' }}>Alert Check Interval (sec)</label>
            <input type="number" placeholder="30" disabled className="px-3 py-2 text-sm w-full opacity-50" style={inputStyle} />
          </div>
        </div>
        <p className="text-xs mt-2" style={{ color: 'rgb(100,116,139)' }}>
          These values are configured via environment variables (RETENTION_DAYS, ALERT_CHECK_INTERVAL).
        </p>
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="mb-8 p-5 rounded-n10" style={{ background: 'rgba(10,18,32,0.7)', border: '0.667px solid rgba(45,212,191,0.15)' }}>
      <h3 className="text-sm font-heading font-bold mb-4 pb-2" style={{ color: 'rgb(224,247,250)', borderBottom: '0.667px solid rgba(45,212,191,0.15)' }}>
        {title}
      </h3>
      {children}
    </div>
  )
}
