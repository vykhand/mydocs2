<script setup lang="ts">
import { ref } from 'vue'
import type { DocumentPage, HighlightRect } from '@/types'
import { getPageImageUrl } from '@/api/documents'
import PageImageViewer from './PageImageViewer.vue'
import HtmlViewer from './HtmlViewer.vue'
import MarkdownViewer from './MarkdownViewer.vue'

const props = defineProps<{
  page: DocumentPage
  documentId: string
  zoom: number
  highlights?: HighlightRect[]
}>()

type PageTab = 'image' | 'html' | 'markdown'
const activeTab = ref<PageTab>('image')

const tabs: { key: PageTab; label: string }[] = [
  { key: 'image', label: 'Page View' },
  { key: 'html', label: 'HTML' },
  { key: 'markdown', label: 'Markdown' },
]
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Tab bar -->
    <div class="flex shrink-0" style="border-bottom: 1px solid var(--color-border);">
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

    <!-- Tab content -->
    <div class="flex-1 min-h-0">
      <PageImageViewer
        v-if="activeTab === 'image'"
        :image-url="getPageImageUrl(documentId, page.page_number)"
        :highlights="highlights"
        :zoom="zoom"
      />
      <HtmlViewer
        v-else-if="activeTab === 'html'"
        :content="page.content_html || ''"
      />
      <MarkdownViewer
        v-else-if="activeTab === 'markdown'"
        :content="page.content_markdown || ''"
      />
    </div>
  </div>
</template>
