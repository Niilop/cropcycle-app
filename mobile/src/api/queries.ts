import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from './client'
import type {
  Bed,
  BedWrite,
  Crop,
  CropFamily,
  Garden,
  GardenDetail,
  Planting,
  PlantingWrite,
} from './types'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Do not retry client errors such as 404; a missing garden is handled by the screen.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400) && count < 2,
    },
  },
})

export const keys = {
  gardens: ['gardens'] as const,
  garden: (id: number) => ['garden', id] as const,
  plantings: (gardenId: number) => ['garden-plantings', gardenId] as const,
  crops: ['crops'] as const,
  families: ['crop-families'] as const,
}

export function useGardens() {
  return useQuery({ queryKey: keys.gardens, queryFn: () => api<Garden[]>('/gardens') })
}

/** The garden with all beds, archived ones included (history still names them). */
export function useGarden(id: number | null) {
  return useQuery({
    queryKey: keys.garden(id ?? 0),
    queryFn: () => api<GardenDetail>(`/gardens/${id}?include_archived=true`),
    enabled: id !== null,
  })
}

export function useGardenPlantings(gardenId: number | null) {
  return useQuery({
    queryKey: keys.plantings(gardenId ?? 0),
    queryFn: () => api<Planting[]>(`/gardens/${gardenId}/plantings`),
    enabled: gardenId !== null,
  })
}

// The catalogue changes only with a seed update.
export function useCrops() {
  return useQuery({
    queryKey: keys.crops,
    queryFn: () => api<Crop[]>('/crops'),
    staleTime: Infinity,
  })
}

export function useFamilies() {
  return useQuery({
    queryKey: keys.families,
    queryFn: () => api<CropFamily[]>('/crop-families'),
    staleTime: Infinity,
  })
}

export function useCreateGarden() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api<Garden>('/gardens', { method: 'POST', json: { name } }),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.gardens }),
  })
}

export function useCreateBed(gardenId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: BedWrite) =>
      api<Bed>(`/gardens/${gardenId}/beds`, { method: 'POST', json: body }),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.garden(gardenId) }),
  })
}

/** Saves bed geometry and name, showing the change immediately and rolling back on error. */
export function useUpdateBed(gardenId: number) {
  const client = useQueryClient()
  const key = keys.garden(gardenId)
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: BedWrite }) =>
      api<Bed>(`/beds/${id}`, { method: 'PUT', json: body }),
    onMutate: async ({ id, body }) => {
      await client.cancelQueries({ queryKey: key })
      const previous = client.getQueryData<GardenDetail>(key)
      if (previous) {
        client.setQueryData<GardenDetail>(key, {
          ...previous,
          beds: previous.beds.map((bed) => (bed.id === id ? { ...bed, ...body } : bed)),
        })
      }
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) client.setQueryData(key, context.previous)
    },
    onSettled: () => client.invalidateQueries({ queryKey: key }),
  })
}

export function useArchiveBed(gardenId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api<null>(`/beds/${id}`, { method: 'DELETE' }),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.garden(gardenId) }),
  })
}

function usePlantingMutation<V>(gardenId: number, request: (variables: V) => Promise<unknown>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.plantings(gardenId) }),
  })
}

export function useCreatePlanting(gardenId: number) {
  return usePlantingMutation(gardenId, ({ bedId, body }: { bedId: number; body: PlantingWrite }) =>
    api<Planting>(`/beds/${bedId}/plantings`, { method: 'POST', json: body }),
  )
}

export function useUpdatePlanting(gardenId: number) {
  return usePlantingMutation(gardenId, ({ id, body }: { id: number; body: PlantingWrite }) =>
    api<Planting>(`/plantings/${id}`, { method: 'PUT', json: body }),
  )
}

export function useDeletePlanting(gardenId: number) {
  return usePlantingMutation(gardenId, (id: number) =>
    api<null>(`/plantings/${id}`, { method: 'DELETE' }),
  )
}
