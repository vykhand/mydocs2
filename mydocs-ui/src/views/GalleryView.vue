<script setup lang="ts">
import { computed, watch, onMounted, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useDocumentsStore } from '@/stores/documents'
import GalleryToolbar from '@/components/gallery/GalleryToolbar.vue'
import DocumentGrid from '@/components/gallery/DocumentGrid.vue'
import SearchResultsList from '@/components/gallery/SearchResultsList.vue'
import UploadModal from '@/components/gallery/UploadModal.vue'
import SettingsDrawer from '@/components/gallery/SettingsDrawer.vue'
import BulkActionsBar from '@/components/documents/BulkActionsBar.vue'
import PaginationBar from '@/components/common/PaginationBar.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { search as searchApi } from '@/api/search'
import type { SearchResponse } from '@/types'
import { ref } from 'vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const docsStore = useDocumentsStore()

const searchResults = ref<SearchResponse | null>(null)
const searchLoading = ref(false)

const hasSearchQuery = computed(() => !!route.query.q)
const showUploadModal = computed(() => route.meta.modal === 'upload')
const showSettingsDrawer = computed(() => route.meta.modal === 'settings')

// Sync URL filters to store
function syncUrlToStore() {
  const q = route.query
  docsStore.filters.search = (q.q as string) || undefined
  docsStore.filters.status = (q.status as string) || undefined
  docsStore.filters.file_type = (q.file_type as string) || undefined
  docsStore.filters.tags = (q.tags as string) || undefined
  docsStore.filters.sort_by = (q.sort_by as string) || 'created_at'
  docsStore.filters.sort_order = (q.sort_order as string) || 'desc'
  docsStore.filters.document_type = (q.document_type as string) || undefined
  docsStore.filters.date_from = (q.date_from as string) || undefined
  docsStore.filters.date_to = (q.date_to as string) || undefined
}

// When there's a search query, run page-level hybrid search
async function runSearch() {
  const query = route.query.q as string
  if (!query) {
    searchResults.value = null
    return
  }
  searchLoading.value = true
  try {
    searchResults.value = await searchApi({
      query,
      search_target: 'pages',
      search_mode: 'hybrid',
      filters: {
        status: docsStore.filters.status || undefined,
        file_type: docsStore.filters.file_type || undefined,
        tags: docsStore.filters.tags ? docsStore.filters.tags.split(',') : undefined,
        document_type: docsStore.filters.document_type || undefined,
      },
      top_k: 20,
    })
  } catch {
    searchResults.value = null
  } finally {
    searchLoading.value = false
  }
}

// Watch for route changes
watch(() => route.query, () => {
  syncUrlToStore()
  if (hasSearchQuery.value) {
    runSearch()
  } else {
    searchResults.value = null
    docsStore.fetchDocuments()
  }
}, { deep: true })

// Set search context on store when opening viewer from search results
watch(() => appStore.viewerDocumentId, (newId) => {
  if (newId && searchResults.value?.results?.length) {
    const query = (route.query.q as string) || ''
    const idx = searchResults.value.results.findIndex(
      r => r.document_id === newId && r.page_number === appStore.viewerPage
    )
    appStore.setViewerSearchContext(searchResults.value.results, query, Math.max(0, idx))
  }
})

onMounted(() => {
  syncUrlToStore()
  if (hasSearchQuery.value) {
    runSearch()
  } else {
    docsStore.fetchDocuments()
  }
})
</script>

<template>
  <div class="space-y-4">
    <GalleryToolbar :result-count="hasSearchQuery ? (searchResults?.total || 0) : docsStore.total" />

    <!-- Bulk actions -->
    <BulkActionsBar v-if="docsStore.selectedIds.size > 0" />

    <!-- Search results mode -->
    <template v-if="hasSearchQuery">
      <LoadingSkeleton v-if="searchLoading" />
      <SearchResultsList
        v-else-if="searchResults && searchResults.results.length"
        :results="searchResults.results"
      />
      <EmptyState
        v-else
        title="No results found"
        message="Try a different search term or adjust your filters."
      />
    </template>

    <!-- Document gallery mode -->
    <template v-else>
      <LoadingSkeleton v-if="docsStore.loading" />
      <DocumentGrid
        v-else-if="docsStore.documents.length"
        :documents="docsStore.documents"
      />
      <EmptyState
        v-else
        title="No documents yet"
        message="Upload your first file to get started."
      />
    </template>

    <!-- Pagination (documents mode only) -->
    <PaginationBar
      v-if="!hasSearchQuery && docsStore.total > (docsStore.filters.page_size || 25)"
      :total="docsStore.total"
      :page="docsStore.filters.page || 1"
      :page-size="docsStore.filters.page_size || 25"
      @update:page="(p: number) => { docsStore.filters.page = p; docsStore.fetchDocuments() }"
    />

    <!-- Upload modal overlay -->
    <UploadModal v-if="showUploadModal" @close="router.push('/')" />

    <!-- Settings drawer overlay -->
    <SettingsDrawer v-if="showSettingsDrawer" @close="router.push('/')" />
  </div>
</template>
