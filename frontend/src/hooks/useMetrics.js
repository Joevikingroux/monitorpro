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

export function useMetricHistory(machineId, from, to, interval) {
  return useQuery({
    queryKey: ['metric-history', machineId, from, to, interval],
    queryFn: async () => {
      const params = {}
      if (from) params.from = from
      if (to) params.to = to
      if (interval) params.interval = interval
      const { data } = await client.get(`/metrics/${machineId}`, { params })
      return data
    },
    enabled: !!machineId,
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
