import api from './client'
import type { ExtractionRequest, ExtractionResponse, FieldResultRecord } from '@/types'

export async function extractFields(request: ExtractionRequest): Promise<ExtractionResponse> {
  const { data } = await api.post('/extract', request)
  return data
}

export async function getFieldResults(documentId: string): Promise<FieldResultRecord[]> {
  const { data } = await api.get('/field-results', { params: { document_id: documentId } })
  return data
}
