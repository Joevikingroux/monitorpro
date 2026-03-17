import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'

export function useCompanies() {
  return useQuery({
    queryKey: ['companies'],
    queryFn: async () => {
      const { data } = await client.get('/companies/')
      return data
    },
  })
}

export function useCompany(id) {
  return useQuery({
    queryKey: ['company', id],
    queryFn: async () => {
      const { data } = await client.get(`/companies/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateCompany() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data) => {
      const resp = await client.post('/companies/', data)
      return resp.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  })
}

export function useUpdateCompany() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...data }) => {
      const resp = await client.patch(`/companies/${id}`, data)
      return resp.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  })
}

export function useDeleteCompany() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await client.delete(`/companies/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  })
}

export function useRegenerateToken() {
  return useMutation({
    mutationFn: async (id) => {
      const resp = await client.post(`/companies/${id}/token`)
      return resp.data
    },
  })
}
