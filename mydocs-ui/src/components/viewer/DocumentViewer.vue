<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Document } from '@/types'
import PdfViewer from './PdfViewer.vue'
import ImageViewer from './ImageViewer.vue'
import MarkdownViewer from './MarkdownViewer.vue'

const props = defineProps<{
  document: Document
  currentPage: number
  zoom: number
  fileUrl: string
  highlightQuery?: string
}>()

const emit = defineEmits<{
  goToPage: [page: number]
  totalPagesResolved: [total: number]
}>()

type DocTab = 'pdf' | 'markdown'
const activeTab = ref<DocTab>('pdf')

const isPdf = computed(() => props.document.file_type === 'pdf')
const isImage = computed(() => ['jpeg', 'png', 'bmp', 'tiff'].includes(props.document.file_type))

// Show tabs only for PDF documents (images don't have meaningful markdown)
const showTabs = computed(() => isPdf.value)

const tabs: { key: DocTab; label: string }[] = [
  { key: 'pdf', label: 'PDF' },
  { key: 'markdown', label: 'Markdown' },
]
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Tab bar (only for PDFs) -->
    <div v-if="showTabs" class="flex shrink-0" style="border-bottom: 1px solid var(--color-border);">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="px-3 py-2 text-xs font-medium transition-colors"
        :style="{
          color: activeTab === tab.key ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          borderBottom: activeTab === tab.key ? '2px solid var(--color-accent)' : '2px solid transparent',
        }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Content area -->
    <div class="flex-1 min-h-0">
      <!-- PDF tab or default for PDFs -->
      <template v-if="isPdf">
        <PdfViewer
          v-if="activeTab === 'pdf'"
          :file-url="fileUrl"
          :page="currentPage"
          :zoom="zoom"
          :highlight-query="highlightQuery"
          @total-pages-resolved="(n: number) => emit('totalPagesResolved', n)"
        />
        <MarkdownViewer
          v-else-if="activeTab === 'markdown'"
          :content="document.content || ''"
        />
      </template>

      <!-- Image viewer -->
      <ImageViewer
        v-else-if="isImage"
        :file-url="fileUrl"
        :zoom="zoom"
      />

      <!-- No preview -->
      <div v-else class="flex items-center justify-center h-full" style="color: var(--color-text-secondary);">
        <p class="text-sm">Preview not available for this file type.</p>
      </div>
    </div>
  </div>
</template>
