import { create } from 'zustand'
import client from '../api/client'

const useAuthStore = create((set) => ({
  user: localStorage.getItem('access_token') ? { email: 'admin' } : null,
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (email, password) => {
    const { data } = await client.post('/auth/login', { email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    set({ user: { email }, isAuthenticated: true })
    return data
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
    window.location.href = '/login'
  },

  changePassword: async (currentPassword, newPassword) => {
    await client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}))

export default useAuthStore
