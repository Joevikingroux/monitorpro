import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'

export function useMachines(companyId) {
  return useQuery({
    queryKey: ['machines', companyId],
    queryFn: async () => {
      const params = companyId ? { company_id: companyId } : {}
      const { data } = await client.get('/machines/', { params })
      return data
    },
    refetchInterval: 30000,
  })
}

export function useMachine(id) {
  return useQuery({
    queryKey: ['machine', id],
    queryFn: async () => {
      const { data } = await client.get(`/machines/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useMachineServices(id) {
  return useQuery({
    queryKey: ['machine-services', id],
    queryFn: async () => {
      const { data } = await client.get(`/machines/${id}/services`)
      return data
    },
    enabled: !!id,
  })
}

export function useMachineSoftware(id) {
  return useQuery({
    queryKey: ['machine-software', id],
    queryFn: async () => {
      const { data } = await client.get(`/machines/${id}/software`)
      return data
    },
    enabled: !!id,
  })
}

export function useMachineEventLogs(id) {
  return useQuery({
    queryKey: ['machine-events', id],
    queryFn: async () => {
      const { data } = await client.get(`/machines/${id}/event-logs`)
      return data
    },
    enabled: !!id,
  })
}

export function useUpdateMachine() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...data }) => {
      const resp = await client.patch(`/machines/${id}`, data)
      return resp.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['machines'] }),
  })
}

export function useDeleteMachine() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await client.delete(`/machines/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['machines'] }),
  })
}
