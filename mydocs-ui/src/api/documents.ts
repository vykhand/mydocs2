import api from './client'
import type {
  Document,
  DocumentListParams,
  DocumentListResponse,
  DocumentPage,
  IngestRequest,
  IngestResponse,
  ParseResponse,
  BatchParseResponse,
} from '@/types'

export async function listDocuments(params: DocumentListParams = {}): Promise<DocumentListResponse> {
  const { data } = await api.get('/documents', { params })
  return data
}

export async function getDocument(id: string): Promise<Document> {
  const { data } = await api.get(`/documents/${id}`)
  return data
}

export async function uploadAndIngest(
  files: File[],
  tags: string[] = [],
  storageMode = 'managed',
  parseAfterUpload = false,
  onProgress?: (pct: number) => void,
): Promise<IngestResponse> {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  formData.append('tags', tags.join(','))
  formData.append('storage_mode', storageMode)
  formData.append('parse_after_upload', String(parseAfterUpload))

  const { data } = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    },
  })
  return data
}

export async function ingestFromPath(request: IngestRequest): Promise<IngestResponse> {
  const { data } = await api.post('/documents/ingest', request)
  return data
}

export async function batchParse(
  documentIds?: string[],
  tags?: string[],
  statusFilter?: string,
): Promise<BatchParseResponse> {
  const { data } = await api.post('/documents/parse', {
    document_ids: documentIds,
    tags,
    status_filter: statusFilter,
  })
  return data
}

export async function parseSingle(
  documentId: string,
  parserConfigOverride?: Record<string, any>,
): Promise<ParseResponse> {
  const { data } = await api.post(`/documents/${documentId}/parse`, {
    parser_config_override: parserConfigOverride || null,
  })
  return data
}

export async function getPages(documentId: string): Promise<DocumentPage[]> {
  const { data } = await api.get(`/documents/${documentId}/pages`)
  return data
}

export async function getPage(documentId: string, pageNumber: number): Promise<DocumentPage> {
  const { data } = await api.get(`/documents/${documentId}/pages/${pageNumber}`)
  return data
}

export async function addTags(documentId: string, tags: string[]): Promise<Document> {
  const { data } = await api.post(`/documents/${documentId}/tags`, { tags })
  return data
}

export async function removeTag(documentId: string, tag: string): Promise<Document> {
  const { data } = await api.delete(`/documents/${documentId}/tags/${tag}`)
  return data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/documents/${documentId}`)
}

export function getDocumentFileUrl(documentId: string): string {
  return `/api/v1/documents/${documentId}/file`
}

export function getPageThumbnailUrl(documentId: string, pageNumber: number, width = 300): string {
  return `/api/v1/documents/${documentId}/pages/${pageNumber}/thumbnail?width=${width}`
}
