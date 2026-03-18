import { useQuery } from '@tanstack/react-query'
import client from '../api/client'

export function useLatestMetric(machineId) {
  return useQuery({
    queryKey: ['metric-latest', machineId],
    queryFn: async () => {
      const { data } = await client.get(`/metrics/${machineId}/latest`)
      return data
    },
    enabled: !!machineId,
    refetchInterval: 30000,
  })
}

export function useMetricHistory(machineId, hours = 1) {
  return useQuery({
    queryKey: ['metric-history', machineId, hours],
    queryFn: async () => {
      const from = new Date(Date.now() - hours * 3600 * 1000).toISOString()
      const { data } = await client.get(`/metrics/${machineId}`, { params: { from } })
      return data
    },
    enabled: !!machineId,
    refetchInterval: 30000,
  })
}

export function useProcesses(machineId) {
  return useQuery({
    queryKey: ['processes', machineId],
    queryFn: async () => {
      const { data } = await client.get(`/metrics/${machineId}/processes`)
      return data
    },
    enabled: !!machineId,
    refetchInterval: 30000,
  })
}
