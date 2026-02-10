import { ref, onMounted, onUnmounted, watch } from 'vue'
import { getDocument, getPages, getDocumentFileUrl } from '@/api/documents'
import type { Document, DocumentPage } from '@/types'

export function useDocumentViewer(documentId: string, initialPage = 1) {
  const document = ref<Document | null>(null)
  const pages = ref<DocumentPage[]>([])
  const currentPage = ref(initialPage)
  const totalPages = ref(0)
  const zoom = ref(1.0)
  const loading = ref(true)
  const pdfDoc = ref<any>(null)

  const fileUrl = getDocumentFileUrl(documentId)

  async function loadDocument() {
    loading.value = true
    try {
      document.value = await getDocument(documentId)
      pages.value = await getPages(documentId)
      totalPages.value = document.value.file_metadata?.page_count || pages.value.length || 1
    } finally {
      loading.value = false
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

  onMounted(loadDocument)

  return {
    document,
    pages,
    currentPage,
    totalPages,
    zoom,
    loading,
    pdfDoc,
    fileUrl,
    goToPage,
    nextPage,
    prevPage,
    setZoom,
    fitToWidth,
    fitToPage,
  }
}
