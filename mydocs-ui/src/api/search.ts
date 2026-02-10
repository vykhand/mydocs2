import api from './client'
import type { SearchRequest, SearchResponse, VectorIndexInfo } from '@/types'

export async function search(request: SearchRequest): Promise<SearchResponse> {
  const { data } = await api.post('/search/', request)
  return data
}

export async function getIndices(): Promise<{ pages: VectorIndexInfo[]; documents: VectorIndexInfo[] }> {
  const { data } = await api.get('/search/indices')
  return data
}
