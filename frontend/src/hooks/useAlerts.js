import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'

export function useAlertRules(companyId) {
  return useQuery({
    queryKey: ['alert-rules', companyId],
    queryFn: async () => {
      const params = companyId ? { company_id: companyId } : {}
      const { data } = await client.get('/alerts/rules', { params })
      return data
    },
  })
}

export function useAlertEvents(filters = {}) {
  return useQuery({
    queryKey: ['alert-events', filters],
    queryFn: async () => {
      const { data } = await client.get('/alerts/events', { params: filters })
      return data
    },
  })
}

export function useUnresolvedAlerts() {
  return useQuery({
    queryKey: ['unresolved-alerts'],
    queryFn: async () => {
      const { data } = await client.get('/alerts/events/unresolved')
      return data
    },
    refetchInterval: 60000,
  })
}

export function useCreateAlertRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data) => {
      const resp = await client.post('/alerts/rules', data)
      return resp.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert-rules'] }),
  })
}

export function useUpdateAlertRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...data }) => {
      const resp = await client.patch(`/alerts/rules/${id}`, data)
      return resp.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert-rules'] }),
  })
}

export function useDeleteAlertRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await client.delete(`/alerts/rules/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert-rules'] }),
  })
}

export function useDeleteAlertEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await client.delete(`/alerts/events/${id}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-events'] })
      qc.invalidateQueries({ queryKey: ['unresolved-alerts'] })
    },
  })
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await client.post(`/alerts/events/${id}/acknowledge`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-events'] })
      qc.invalidateQueries({ queryKey: ['unresolved-alerts'] })
    },
  })
}
