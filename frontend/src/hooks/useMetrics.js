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

export function useMetricHistory(machineId, fromDate) {
  return useQuery({
    queryKey: ['metric-history', machineId, fromDate],
    queryFn: async () => {
      const params = {}
      if (fromDate) params.from = fromDate
      const { data } = await client.get(`/metrics/${machineId}`, { params })
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
