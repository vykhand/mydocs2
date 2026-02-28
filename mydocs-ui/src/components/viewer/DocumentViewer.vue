<script setup lang="ts">
import { computed } from 'vue'
import type { Document } from '@/types'
import VuePdfViewer from './VuePdfViewer.vue'
import ImageViewer from './ImageViewer.vue'

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

const isPdf = computed(() => props.document.file_type === 'pdf')
const isImage = computed(() => ['jpeg', 'png', 'bmp', 'tiff'].includes(props.document.file_type))
</script>

<template>
  <div class="h-full">
    <VuePdfViewer
      v-if="isPdf"
      :file-url="fileUrl"
      :page="currentPage"
      :highlight-query="highlightQuery"
      @total-pages-resolved="(t: number) => emit('totalPagesResolved', t)"
    />
    <ImageViewer
      v-else-if="isImage"
      :file-url="fileUrl"
      :zoom="zoom"
    />
    <div v-else class="flex items-center justify-center h-full" style="color: var(--color-text-secondary);">
      <p class="text-sm">Preview not available for this file type.</p>
    </div>
  </div>
</template>
