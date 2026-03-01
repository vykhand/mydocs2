import { ref, onMounted, watch, isRef, type Ref } from 'vue'
import { getDocument, getPages, getPage, getDocumentFileUrl } from '@/api/documents'
import type { Document, DocumentPage } from '@/types'

export function useDocumentViewer(documentId: string | Ref<string | null>, initialPage = 1) {
  const document = ref<Document | null>(null)
  const pages = ref<DocumentPage[]>([])
  const currentPage = ref(initialPage)
  const totalPages = ref(0)
  const zoom = ref(1.0)
  const loading = ref(true)
  const currentPageData = ref<DocumentPage | null>(null)

  const resolveId = () => isRef(documentId) ? documentId.value : documentId
  const fileUrl = ref(resolveId() ? getDocumentFileUrl(resolveId()!) : '')

  async function loadDocument() {
    const id = resolveId()
    if (!id) return
    loading.value = true
    fileUrl.value = getDocumentFileUrl(id)
    try {
      document.value = await getDocument(id)
      pages.value = await getPages(id)
      totalPages.value = document.value.file_metadata?.page_count || pages.value.length || 1
    } finally {
      loading.value = false
    }
  }

  async function loadPageData(pageNumber: number) {
    const id = resolveId()
    if (!id) return
    try {
      currentPageData.value = await getPage(id, pageNumber)
    } catch {
      currentPageData.value = null
    }
  }

  function goToPage(n: number) {
    if (n >= 1 && n <= totalPages.value) {
      currentPage.value = n
    }
  }

  function nextPage() {
    goToPage(currentPage.value + 1)
  }

  function prevPage() {
    goToPage(currentPage.value - 1)
  }

  function setZoom(level: number) {
    zoom.value = Math.max(0.25, Math.min(5, level))
  }

  function fitToWidth() {
    zoom.value = 1.0
  }

  function fitToPage() {
    zoom.value = 0.85
  }

  // If documentId is a ref, watch for changes
  if (isRef(documentId)) {
    watch(documentId, (newId) => {
      if (newId) {
        currentPage.value = 1
        currentPageData.value = null
        loadDocument()
      }
    })
  }

  onMounted(loadDocument)

  return {
    document,
    pages,
    currentPage,
    totalPages,
    zoom,
    loading,
    currentPageData,
    fileUrl,
    goToPage,
    nextPage,
    prevPage,
    setZoom,
    fitToWidth,
    fitToPage,
    loadPageData,
  }
}
