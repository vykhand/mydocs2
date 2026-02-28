import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { SearchResult, ViewerMode, DocumentViewerTab, PageViewerTab } from '@/types'

export type AppMode = 'simple' | 'advanced'
export type ThemeMode = 'light' | 'dark' | 'system'
export type ActiveTab = 'documents' | 'cases'
export type GalleryViewMode = 'grid' | 'list'

export const useAppStore = defineStore('app', () => {
  const mode = ref<AppMode>('simple')
  const theme = ref<ThemeMode>('system')
  const sidebarCollapsed = ref(false)

  // Layout state
  const viewerOpen = ref(false)
  const viewerDocumentId = ref<string | null>(null)
  const viewerPage = ref<number>(1)
  const activeTab = ref<ActiveTab>('documents')
  const galleryViewMode = ref<GalleryViewMode>('grid')

  // Viewer mode & tabs
  const viewerMode = ref<ViewerMode>('document')
  const viewerActiveDocumentTab = ref<DocumentViewerTab>('pdf')
  const viewerActivePageTab = ref<PageViewerTab>('page-view')

  // Search viewer context
  const viewerHighlightQuery = ref('')
  const viewerSearchResults = ref<SearchResult[]>([])
  const viewerCurrentResultIndex = ref(0)

  function toggleMode() {
    mode.value = mode.value === 'simple' ? 'advanced' : 'simple'
  }

  function setTheme(t: ThemeMode) {
    theme.value = t
    applyTheme()
  }

  function applyTheme() {
    const root = document.documentElement
    if (theme.value === 'dark' || (theme.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function openViewer(id: string, page = 1, highlightQuery = '', modeParam: ViewerMode = 'document') {
    viewerDocumentId.value = id
    viewerPage.value = page
    viewerHighlightQuery.value = highlightQuery
    viewerMode.value = modeParam
    viewerOpen.value = true
    // Reset tabs to defaults for the mode
    if (modeParam === 'document') {
      viewerActiveDocumentTab.value = 'pdf'
    } else {
      viewerActivePageTab.value = 'page-view'
    }
  }

  function switchToPageMode(pageNumber: number) {
    viewerMode.value = 'page'
    viewerPage.value = pageNumber
    viewerActivePageTab.value = 'page-view'
  }

  function switchToDocumentMode() {
    viewerMode.value = 'document'
    viewerActiveDocumentTab.value = 'pdf'
  }

  function closeViewer() {
    viewerOpen.value = false
    viewerDocumentId.value = null
    viewerPage.value = 1
    viewerHighlightQuery.value = ''
    viewerSearchResults.value = []
    viewerCurrentResultIndex.value = 0
    viewerMode.value = 'document'
    viewerActiveDocumentTab.value = 'pdf'
    viewerActivePageTab.value = 'page-view'
  }

  function setViewerSearchContext(results: SearchResult[], query: string, startIndex: number) {
    viewerSearchResults.value = results
    viewerHighlightQuery.value = query
    viewerCurrentResultIndex.value = startIndex
  }

  function nextSearchResult() {
    if (viewerSearchResults.value.length === 0) return
    const nextIdx = (viewerCurrentResultIndex.value + 1) % viewerSearchResults.value.length
    viewerCurrentResultIndex.value = nextIdx
    const result = viewerSearchResults.value[nextIdx]
    viewerDocumentId.value = result.document_id
    viewerPage.value = result.page_number || 1
  }

  function prevSearchResult() {
    if (viewerSearchResults.value.length === 0) return
    const prevIdx = (viewerCurrentResultIndex.value - 1 + viewerSearchResults.value.length) % viewerSearchResults.value.length
    viewerCurrentResultIndex.value = prevIdx
    const result = viewerSearchResults.value[prevIdx]
    viewerDocumentId.value = result.document_id
    viewerPage.value = result.page_number || 1
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'system') applyTheme()
    })
  }

  return {
    mode, theme, sidebarCollapsed,
    viewerOpen, viewerDocumentId, viewerPage, activeTab, galleryViewMode,
    viewerMode, viewerActiveDocumentTab, viewerActivePageTab,
    viewerHighlightQuery, viewerSearchResults, viewerCurrentResultIndex,
    toggleMode, setTheme, applyTheme, toggleSidebar,
    openViewer, closeViewer, switchToPageMode, switchToDocumentMode,
    setViewerSearchContext, nextSearchResult, prevSearchResult,
  }
}, {
  persist: {
    paths: ['mode', 'theme', 'sidebarCollapsed', 'activeTab', 'galleryViewMode'],
  },
})
