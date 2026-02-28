<script setup lang="ts">
import { computed, watch, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import { useDocumentViewer } from '@/composables/useDocumentViewer'
import DocumentViewer from '@/components/viewer/DocumentViewer.vue'
import PageViewer from '@/components/viewer/PageViewer.vue'
import { X, Maximize2, ChevronLeft, ChevronRight, Info, ArrowRight, ArrowLeft } from 'lucide-vue-next'

const panelWidth = defineModel<number>('panelWidth', { default: 420 })

const appStore = useAppStore()
const route = useRoute()
const { isMobile, isTablet } = useResponsive()

const showInfoPanel = ref(false)

const documentId = computed(() => appStore.viewerDocumentId)

const viewer = useDocumentViewer(documentId, appStore.viewerPage)

const isDocumentMode = computed(() => appStore.viewerMode === 'document')
const isPageMode = computed(() => appStore.viewerMode === 'page')

// Current page data for page mode
const currentPageData = computed(() => {
  if (!viewer.pages.value || !viewer.currentPage.value) return null
  return viewer.pages.value.find(p => p.page_number === viewer.currentPage.value) || null
})

// Watch route query for page changes
watch(() => route.query.page, (p) => {
  if (p && viewer) {
    viewer.goToPage(Number(p))
  }
})

// Watch appStore.viewerPage for changes from search result navigation
watch(() => appStore.viewerPage, (newPage) => {
  if (newPage && viewer) {
    viewer.goToPage(newPage)
  }
})

// Horizontal resize handle logic
const isResizing = ref(false)

function onResizeStart(e: MouseEvent) {
  e.preventDefault()
  isResizing.value = true
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}

function onResizeMove(e: MouseEvent) {
  if (!isResizing.value) return
  const newWidth = window.innerWidth - e.clientX
  const maxWidth = Math.floor(window.innerWidth * 0.75)
  panelWidth.value = Math.min(maxWidth, Math.max(300, newWidth))
}

function onResizeEnd() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

// Search result navigation
const hasSearchResults = computed(() => appStore.viewerSearchResults.length > 0)
const searchResultLabel = computed(() => {
  if (!hasSearchResults.value) return ''
  return `Result ${appStore.viewerCurrentResultIndex + 1} of ${appStore.viewerSearchResults.length}`
})

// Header title
const headerTitle = computed(() => {
  const name = viewer.document.value?.original_file_name || 'Document Viewer'
  if (isPageMode.value) {
    return `${name} - Page ${viewer.currentPage.value}`
  }
  return name
})

function goToPageMode() {
  appStore.switchToPageMode(viewer.currentPage.value)
}

function backToDocumentMode() {
  appStore.switchToDocumentMode()
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
})
</script>

<template>
  <aside
    class="relative flex flex-col overflow-hidden"
    :style="{
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <!-- Resize handle -->
    <div
      class="absolute top-0 left-0 bottom-0 w-1.5 cursor-col-resize z-10 hover:bg-[var(--color-accent)]/20 transition-colors"
      :style="{ backgroundColor: isResizing ? 'var(--color-accent)' : 'transparent' }"
      @mousedown="onResizeStart"
    />
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b shrink-0" style="border-color: var(--color-border);">
      <div class="flex items-center gap-2 min-w-0">
        <!-- Back button in page mode -->
        <button
          v-if="isPageMode"
          @click="backToDocumentMode"
          class="p-1 rounded hover:opacity-70 shrink-0"
          style="color: var(--color-text-secondary);"
          title="Back to document"
        >
          <ArrowLeft :size="16" />
        </button>
        <h3 class="text-sm font-semibold truncate" style="color: var(--color-text-primary);">
          {{ headerTitle }}
        </h3>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <button
          @click="showInfoPanel = !showInfoPanel"
          class="p-1 rounded hover:opacity-70"
          :style="{ color: showInfoPanel ? 'var(--color-accent)' : 'var(--color-text-secondary)' }"
          title="Document Info"
        >
          <Info :size="16" />
        </button>
        <button
          class="p-1 rounded hover:opacity-70"
          style="color: var(--color-text-secondary);"
          title="Maximize"
        >
          <Maximize2 :size="16" />
        </button>
        <button
          @click="appStore.closeViewer()"
          class="p-1 rounded hover:opacity-70"
          style="color: var(--color-text-secondary);"
          title="Close"
        >
          <X :size="16" />
        </button>
      </div>
    </div>

    <!-- Content area -->
    <div class="flex-1 min-h-0 relative">
      <!-- Loading spinner -->
      <div v-if="viewer.loading.value" class="flex items-center justify-center h-full">
        <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
      </div>

      <!-- Document Mode -->
      <DocumentViewer
        v-else-if="isDocumentMode && viewer.document.value"
        :document="viewer.document.value"
        :current-page="viewer.currentPage.value"
        :zoom="viewer.zoom.value"
        :file-url="viewer.fileUrl.value"
        :highlight-query="appStore.viewerHighlightQuery"
        @go-to-page="viewer.goToPage"
        @total-pages-resolved="(n: number) => viewer.totalPages.value = n"
        class="h-full"
      />

      <!-- Page Mode -->
      <PageViewer
        v-else-if="isPageMode && currentPageData && viewer.document.value"
        :page="currentPageData"
        :document-id="viewer.document.value.id"
        :zoom="viewer.zoom.value"
        class="h-full"
      />

      <!-- Info panel slide-over -->
      <Transition name="slide">
        <div
          v-if="showInfoPanel && viewer.document.value"
          class="absolute top-0 right-0 bottom-0 w-72 overflow-y-auto border-l z-20"
          style="background-color: var(--color-bg-secondary); border-color: var(--color-border);"
        >
          <div class="p-4 space-y-0">
            <!-- Metadata -->
            <div class="py-3">
              <p class="text-xs font-medium uppercase tracking-wide mb-2" style="color: var(--color-text-secondary);">Metadata</p>
              <div class="space-y-1 text-xs" style="color: var(--color-text-secondary);">
                <p v-if="viewer.document.value?.file_type">Type: {{ viewer.document.value.file_type }}</p>
                <p v-if="viewer.document.value?.status">Status: {{ viewer.document.value.status }}</p>
                <p v-if="viewer.document.value?.file_metadata?.size_bytes">Size: {{ Math.round((viewer.document.value.file_metadata.size_bytes || 0) / 1024) }}KB</p>
                <p v-if="viewer.document.value?.file_metadata?.author">Author: {{ viewer.document.value.file_metadata.author }}</p>
                <p v-if="viewer.document.value?.created_at">Created: {{ new Date(viewer.document.value.created_at).toLocaleDateString() }}</p>
              </div>
            </div>

            <!-- Tags -->
            <div class="border-t py-3" style="border-color: var(--color-border);">
              <p class="text-xs font-medium uppercase tracking-wide mb-2" style="color: var(--color-text-secondary);">Tags</p>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="tag in viewer.document.value?.tags"
                  :key="tag"
                  class="px-2 py-0.5 rounded text-xs"
                  style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
                >
                  {{ tag }}
                </span>
                <span v-if="!viewer.document.value?.tags?.length" class="text-xs" style="color: var(--color-text-secondary);">
                  No tags
                </span>
              </div>
            </div>

            <!-- Duplicates -->
            <div class="border-t py-3" style="border-color: var(--color-border);">
              <p class="text-xs font-medium uppercase tracking-wide mb-2" style="color: var(--color-text-secondary);">Duplicates</p>
              <p class="text-xs" style="color: var(--color-text-secondary);">No duplicates detected.</p>
            </div>

            <!-- Advanced -->
            <div class="border-t py-3" style="border-color: var(--color-border);">
              <p class="text-xs font-medium uppercase tracking-wide mb-2" style="color: var(--color-text-secondary);">Advanced</p>
              <div class="text-xs space-y-1" style="color: var(--color-text-secondary);">
                <p>ID: {{ viewer.document.value?.id }}</p>
                <p v-if="viewer.document.value?.parser_engine">Parser: {{ viewer.document.value.parser_engine }}</p>
                <p v-if="viewer.document.value?.parser_config_hash">Config Hash: {{ viewer.document.value.parser_config_hash }}</p>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Bottom toolbar -->
    <div
      class="flex items-center justify-between px-4 py-2 border-t shrink-0"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <!-- Page navigation -->
      <div class="flex items-center gap-2">
        <button
          @click="viewer.prevPage()"
          :disabled="viewer.currentPage.value === 1"
          class="p-1 rounded border disabled:opacity-40 hover:opacity-70"
          style="border-color: var(--color-border); color: var(--color-text-primary);"
          title="Previous page"
        >
          <ChevronLeft :size="14" />
        </button>
        <span class="text-xs tabular-nums" style="color: var(--color-text-secondary);">
          Page {{ viewer.currentPage.value }} / {{ viewer.totalPages.value }}
        </span>
        <button
          @click="viewer.nextPage()"
          :disabled="viewer.currentPage.value === viewer.totalPages.value"
          class="p-1 rounded border disabled:opacity-40 hover:opacity-70"
          style="border-color: var(--color-border); color: var(--color-text-primary);"
          title="Next page"
        >
          <ChevronRight :size="14" />
        </button>

        <!-- Go to Page button (document mode only) -->
        <button
          v-if="isDocumentMode"
          @click="goToPageMode"
          class="flex items-center gap-1 px-2 py-1 rounded text-xs hover:opacity-70"
          style="color: var(--color-accent);"
          title="View page details"
        >
          Go to Page
          <ArrowRight :size="12" />
        </button>
      </div>

      <!-- Search result navigation -->
      <div v-if="hasSearchResults" class="flex items-center gap-2">
        <span class="text-xs" style="color: var(--color-text-secondary);">{{ searchResultLabel }}</span>
        <button
          @click="appStore.prevSearchResult()"
          class="p-1 rounded border hover:opacity-70"
          style="border-color: var(--color-border); color: var(--color-text-primary);"
          title="Previous result"
        >
          <ChevronLeft :size="14" />
        </button>
        <button
          @click="appStore.nextSearchResult()"
          class="p-1 rounded border hover:opacity-70"
          style="border-color: var(--color-border); color: var(--color-text-primary);"
          title="Next result"
        >
          <ChevronRight :size="14" />
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
