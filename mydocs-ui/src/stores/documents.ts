import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Document, DocumentListParams } from '@/types'
import { listDocuments } from '@/api/documents'
import { useTagsStore } from './tags'

export const useDocumentsStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const total = ref(0)
  const loading = ref(false)
  const selectedIds = ref<Set<string>>(new Set())

  const filters = reactive<DocumentListParams>({
    page: 1,
    page_size: 25,
    status: undefined,
    file_type: undefined,
    tags: undefined,
    sort_by: 'created_at',
    sort_order: 'desc',
    search: undefined,
  })

  async function fetchDocuments() {
    loading.value = true
    try {
      const params: DocumentListParams = { ...filters }
      // Clean undefined values
      Object.keys(params).forEach(k => {
        if ((params as any)[k] === undefined || (params as any)[k] === '') {
          delete (params as any)[k]
        }
      })
      const resp = await listDocuments(params)
      documents.value = resp.documents
      total.value = resp.total
      // Update tag cache
      useTagsStore().updateFromDocuments(resp.documents)
    } finally {
      loading.value = false
    }
  }

  function toggleSelect(id: string) {
    if (selectedIds.value.has(id)) {
      selectedIds.value.delete(id)
    } else {
      selectedIds.value.add(id)
    }
  }

  function selectAll() {
    documents.value.forEach(d => selectedIds.value.add(d.id))
  }

  function clearSelection() {
    selectedIds.value.clear()
  }

  return {
    documents, total, loading, selectedIds, filters,
    fetchDocuments, toggleSelect, selectAll, clearSelection,
  }
})
