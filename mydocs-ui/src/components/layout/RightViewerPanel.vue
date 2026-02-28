<script setup lang="ts">
import { computed, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import { useDocumentViewer } from '@/composables/useDocumentViewer'
import DocumentViewer from '@/components/viewer/DocumentViewer.vue'
import MarkdownViewer from '@/components/viewer/MarkdownViewer.vue'
import HtmlViewer from '@/components/viewer/HtmlViewer.vue'
import PageImageViewer from '@/components/viewer/PageImageViewer.vue'
import { X, Maximize2, ChevronLeft, ChevronRight, Info } from 'lucide-vue-next'
import { ref } from 'vue'

const panelWidth = defineModel<number>('panelWidth', { default: 420 })

const appStore = useAppStore()
const route = useRoute()
const { isMobile, isTablet } = useResponsive()

const showInfoPanel = ref(false)

const documentId = computed(() => appStore.viewerDocumentId)

const viewer = useDocumentViewer(documentId, appStore.viewerPage)

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

// Load page data when in page mode and page changes
watch([() => appStore.viewerMode, () => viewer.currentPage.value], ([mode, page]) => {
  if (mode === 'page' && page) {
    viewer.loadPageData(page)
  }
}, { immediate: true })

// Handle totalPagesResolved from VuePdfViewer
function onTotalPagesResolved(total: number) {
  viewer.totalPages.value = total
}

// Tab definitions
const documentTabs = [
  { key: 'pdf' as const, label: 'PDF' },
  { key: 'markdown' as const, label: 'Markdown' },
]

const pageTabs = [
  { key: 'page-view' as const, label: 'Page View' },
  { key: 'html' as const, label: 'HTML' },
  { key: 'markdown' as const, label: 'Markdown' },
]

const activeTabs = computed(() =>
  appStore.viewerMode === 'document' ? documentTabs : pageTabs
)

const activeTabKey = computed(() =>
  appStore.viewerMode === 'document'
    ? appStore.viewerActiveDocumentTab
    : appStore.viewerActivePageTab
)

function setActiveTab(key: string) {
  if (appStore.viewerMode === 'document') {
    appStore.viewerActiveDocumentTab = key as 'pdf' | 'markdown'
  } else {
    appStore.viewerActivePageTab = key as 'page-view' | 'html' | 'markdown'
  }
}

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

// Handle go-to-page from markdown viewer (switch to page mode)
function handleGoToPage(page: number) {
  appStore.switchToPageMode(page)
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
      <h3 class="text-sm font-semibold truncate" style="color: var(--color-text-primary);">
        {{ viewer.document.value?.original_file_name || 'Document Viewer' }}
      </h3>
      <div class="flex items-center gap-1">
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

    <!-- Tab bar -->
    <div class="flex border-b shrink-0" style="border-color: var(--color-border);">
      <button
        v-for="tab in activeTabs"
        :key="tab.key"
        @click="setActiveTab(tab.key)"
        class="flex-1 py-2 text-xs font-medium transition-colors border-b-2"
        :style="{
          color: activeTabKey === tab.key ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          borderBottomColor: activeTabKey === tab.key ? 'var(--color-accent)' : 'transparent',
        }"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Content area -->
    <div class="flex-1 min-h-0 relative">
      <!-- Loading spinner -->
      <div v-if="viewer.loading.value" class="flex items-center justify-center h-full">
        <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
      </div>

      <template v-else-if="viewer.document.value">
        <!-- DOCUMENT MODE -->
        <template v-if="appStore.viewerMode === 'document'">
          <!-- PDF tab -->
          <DocumentViewer
            v-if="appStore.viewerActiveDocumentTab === 'pdf'"
            :document="viewer.document.value"
            :current-page="viewer.currentPage.value"
            :zoom="viewer.zoom.value"
            :file-url="viewer.fileUrl.value"
            :highlight-query="appStore.viewerHighlightQuery"
            @go-to-page="viewer.goToPage"
            @total-pages-resolved="onTotalPagesResolved"
            class="h-full"
          />
          <!-- Markdown tab -->
          <MarkdownViewer
            v-else-if="appStore.viewerActiveDocumentTab === 'markdown'"
            :content="viewer.document.value.content || ''"
            :page-count="viewer.totalPages.value"
            @go-to-page="handleGoToPage"
            class="h-full"
          />
        </template>

        <!-- PAGE MODE -->
        <template v-else>
          <!-- Page View tab -->
          <PageImageViewer
            v-if="appStore.viewerActivePageTab === 'page-view'"
            :document-id="viewer.document.value.id"
            :page-number="viewer.currentPage.value"
            class="h-full"
          />
          <!-- HTML tab -->
          <HtmlViewer
            v-else-if="appStore.viewerActivePageTab === 'html'"
            :content="viewer.currentPageData.value?.content_html || ''"
            class="h-full"
          />
          <!-- Markdown tab -->
          <MarkdownViewer
            v-else-if="appStore.viewerActivePageTab === 'markdown'"
            :content="viewer.currentPageData.value?.content_markdown || ''"
            @go-to-page="handleGoToPage"
            class="h-full"
          />
        </template>
      </template>

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
      </div>

      <!-- Mode indicator -->
      <span
        v-if="appStore.viewerMode === 'page'"
        class="text-xs px-2 py-0.5 rounded cursor-pointer hover:opacity-80"
        style="background-color: var(--color-bg-tertiary); color: var(--color-accent);"
        @click="appStore.switchToDocumentMode()"
        title="Switch to document mode"
      >
        Page Mode
      </span>

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
