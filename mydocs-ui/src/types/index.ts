// Enums
export type FileType = 'unknown' | 'pdf' | 'txt' | 'docx' | 'xlsx' | 'pptx' | 'jpeg' | 'png' | 'bmp' | 'tiff'
export type StorageMode = 'managed' | 'external'
export type StorageBackend = 'local' | 'azure_blob' | 's3' | 'gcs' | 'onedrive'
export type DocumentStatus = 'new' | 'parsing' | 'parsed' | 'failed' | 'skipped' | 'not_supported'
export type DocumentElementType = 'paragraph' | 'table' | 'key_value_pair' | 'image' | 'barcode'
export type DocumentType = 'generic'
export type SearchMode = 'fulltext' | 'vector' | 'hybrid'
export type SearchTarget = 'pages' | 'documents'

// Models
export interface FileMetadata {
  size_bytes?: number
  mime_type?: string
  created_at?: string
  modified_at?: string
  crc32?: string
  sha256?: string
  page_count?: number
  author?: string
  title?: string
  subject?: string
  image_width?: number
  image_height?: number
}

export interface DocumentElement {
  id: string
  page_id: string
  page_number: number
  offset: number
  short_id?: string
  type: DocumentElementType
  element_data: Record<string, any>
}

export interface Document {
  id: string
  file_name: string
  original_file_name: string
  file_type: FileType
  original_path: string
  storage_mode: StorageMode
  storage_backend: StorageBackend
  managed_path?: string
  file_metadata?: FileMetadata
  status: DocumentStatus
  document_type: DocumentType
  locked: boolean
  content?: string
  content_type?: string
  parser_engine?: string
  parser_config_hash?: string
  elements?: DocumentElement[]
  tags: string[]
  created_at?: string
  modified_at?: string
}

export interface DocumentPage {
  id: string
  document_id: string
  page_number: number
  content?: string
  content_markdown?: string
  content_html?: string
  height?: number
  width?: number
  unit?: string
}

// API Request/Response
export interface DocumentListResponse {
  documents: Document[]
  total: number
  page: number
  page_size: number
}

export interface DocumentListParams {
  page?: number
  page_size?: number
  status?: string
  file_type?: string
  tags?: string
  sort_by?: string
  sort_order?: string
  search?: string
}

export interface IngestRequest {
  source: string | string[]
  storage_mode?: string
  tags?: string[]
  recursive?: boolean
}

export interface IngestResponse {
  documents: Array<{ id: string; file_name: string; status: string }>
  skipped: Array<{ path: string; reason: string }>
}

export interface ParseResponse {
  document_id: string
  status: string
  page_count: number
  element_count: number
}

export interface BatchParseResponse {
  queued: number
  skipped: number
}

// Search
export interface FuzzyConfig {
  enabled: boolean
  max_edits: number
  prefix_length: number
}

export interface FullTextSearchConfig {
  enabled: boolean
  content_field: string
  fuzzy: FuzzyConfig
  score_boost: number
}

export interface VectorSearchConfig {
  enabled: boolean
  index_name?: string
  embedding_model?: string
  num_candidates: number
  score_boost: number
}

export interface HybridSearchConfig {
  combination_method: string
  rrf_k: number
  weights: { fulltext: number; vector: number }
}

export interface SearchFilters {
  tags?: string[]
  file_type?: string
  document_ids?: string[]
  status?: string
  document_type?: string
}

export interface SearchRequest {
  query: string
  search_target: SearchTarget
  search_mode: SearchMode
  fulltext?: FullTextSearchConfig
  vector?: VectorSearchConfig
  hybrid?: HybridSearchConfig
  filters?: SearchFilters
  top_k?: number
  min_score?: number
  include_content_fields?: string[]
}

export interface SearchResult {
  id: string
  document_id: string
  page_number?: number
  score: number
  scores: Record<string, number>
  content?: string
  content_markdown?: string
  file_name?: string
  tags: string[]
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  search_target: string
  search_mode: string
  vector_index_used?: string
  embedding_model_used?: string
}

export interface VectorIndexInfo {
  index_name: string
  embedding_model: string
  field: string
  dimensions: number
  similarity: string
}

export interface HighlightRect {
  x: number
  y: number
  width: number
  height: number
  text?: string
  elementId?: string
  elementType?: DocumentElementType
}
