import api from './client'
import type { ExtractionRequest, ExtractionResponse, FieldResultRecord, SplitClassifyResult } from '@/types'

export async function extractFields(request: ExtractionRequest): Promise<ExtractionResponse> {
  const { data } = await api.post('/extract', request)
  return data
}

export async function getFieldResults(documentId: string): Promise<FieldResultRecord[]> {
  const { data } = await api.get('/field-results', { params: { document_id: documentId } })
  return data
}

export async function splitClassify(documentId: string, caseType = 'generic'): Promise<SplitClassifyResult> {
  const { data } = await api.post('/split-classify', {
    document_ids: [documentId],
    case_type: caseType,
    document_type: 'generic',
  })
  return data
}
