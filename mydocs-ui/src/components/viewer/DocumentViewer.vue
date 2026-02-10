<script setup lang="ts">
import { computed } from 'vue'
import type { Document } from '@/types'
import PdfViewer from './PdfViewer.vue'
import ImageViewer from './ImageViewer.vue'

const props = defineProps<{
  document: Document
  currentPage: number
  zoom: number
  fileUrl: string
}>()

const emit = defineEmits<{
  goToPage: [page: number]
}>()

const isPdf = computed(() => props.document.file_type === 'pdf')
const isImage = computed(() => ['jpeg', 'png', 'bmp', 'tiff'].includes(props.document.file_type))
</script>

<template>
  <div class="h-full">
    <PdfViewer
      v-if="isPdf"
      :file-url="fileUrl"
      :page="currentPage"
      :zoom="zoom"
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
