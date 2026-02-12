import api from './client'
import type { Case, CaseListResponse, DocumentListResponse } from '@/types'

export async function listCases(params: { page?: number; page_size?: number; search?: string } = {}): Promise<CaseListResponse> {
  const { data } = await api.get('/cases', { params })
  return data
}

export async function getCase(id: string): Promise<Case> {
  const { data } = await api.get(`/cases/${id}`)
  return data
}

export async function createCase(payload: { name: string; description?: string }): Promise<Case> {
  const { data } = await api.post('/cases', payload)
  return data
}

export async function updateCase(id: string, payload: { name?: string; description?: string }): Promise<Case> {
  const { data } = await api.put(`/cases/${id}`, payload)
  return data
}

export async function deleteCase(id: string): Promise<void> {
  await api.delete(`/cases/${id}`)
}

export async function addDocumentsToCase(caseId: string, documentIds: string[]): Promise<Case> {
  const { data } = await api.post(`/cases/${caseId}/documents`, { document_ids: documentIds })
  return data
}

export async function removeDocumentFromCase(caseId: string, documentId: string): Promise<Case> {
  const { data } = await api.delete(`/cases/${caseId}/documents/${documentId}`)
  return data
}

export async function getCaseDocuments(caseId: string, params: { page?: number; page_size?: number } = {}): Promise<DocumentListResponse> {
  const { data } = await api.get(`/cases/${caseId}/documents`, { params })
  return data
}
