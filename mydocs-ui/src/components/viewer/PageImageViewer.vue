<script setup lang="ts">
import { ref } from 'vue'
import { getPageThumbnailUrl } from '@/api/documents'

const props = defineProps<{
  documentId: string
  pageNumber: number
}>()

const zoom = ref(1)
const imgRef = ref<HTMLImageElement>()

// Use a large width for high-res page image
const imageUrl = ref(getPageThumbnailUrl(props.documentId, props.pageNumber, 1200))

function onWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    zoom.value = Math.max(0.25, Math.min(5, zoom.value + delta))
  }
}
</script>

<template>
  <div class="h-full w-full overflow-auto" style="background-color: var(--color-bg-tertiary);" @wheel="onWheel">
    <div class="flex justify-center p-4">
      <img
        ref="imgRef"
        :src="imageUrl"
        :style="{ transform: `scale(${zoom})`, transformOrigin: 'top center' }"
        class="max-w-full transition-transform"
        alt="Page image"
      />
    </div>
  </div>
</template>
