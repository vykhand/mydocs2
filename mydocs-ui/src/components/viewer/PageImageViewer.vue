<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { HighlightRect } from '@/types'

const props = defineProps<{
  imageUrl: string
  highlights?: HighlightRect[]
  zoom?: number
}>()

const loading = ref(true)
const error = ref(false)
const imgRef = ref<HTMLImageElement | null>(null)
const naturalWidth = ref(0)
const naturalHeight = ref(0)

const effectiveZoom = computed(() => props.zoom || 1)

function handleLoad(e: Event) {
  const img = e.target as HTMLImageElement
  naturalWidth.value = img.naturalWidth
  naturalHeight.value = img.naturalHeight
  loading.value = false
  error.value = false
}

function handleError() {
  loading.value = false
  error.value = true
}

watch(() => props.imageUrl, () => {
  loading.value = true
  error.value = false
})

// Convert highlight rects to CSS positions relative to image display size
const scaledHighlights = computed(() => {
  if (!props.highlights || !naturalWidth.value) return []
  return props.highlights.map(h => ({
    ...h,
    left: `${(h.x / naturalWidth.value) * 100}%`,
    top: `${(h.y / naturalHeight.value) * 100}%`,
    width: `${(h.width / naturalWidth.value) * 100}%`,
    height: `${(h.height / naturalHeight.value) * 100}%`,
  }))
})
</script>

<template>
  <div class="h-full w-full overflow-auto flex items-start justify-center p-2" style="background-color: var(--color-bg-tertiary);">
    <div v-if="loading" class="flex items-center justify-center h-full">
      <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
    </div>
    <div v-if="error" class="flex flex-col items-center justify-center h-full gap-2 p-4">
      <p class="text-sm font-medium" style="color: var(--color-danger);">Image Error</p>
      <p class="text-xs" style="color: var(--color-text-secondary);">Failed to load page image.</p>
    </div>
    <div v-show="!error" class="page-image-wrapper relative inline-block" :style="{ transform: `scale(${effectiveZoom})`, transformOrigin: 'top center' }">
      <img
        ref="imgRef"
        :src="imageUrl"
        class="block max-w-full"
        @load="handleLoad"
        @error="handleError"
      />
      <!-- Highlight overlays -->
      <div
        v-for="(hl, idx) in scaledHighlights"
        :key="idx"
        class="absolute pointer-events-none"
        :style="{
          left: hl.left,
          top: hl.top,
          width: hl.width,
          height: hl.height,
          background: 'var(--color-highlight, rgba(251, 191, 36, 0.3))',
          border: '1px solid var(--color-highlight, rgba(251, 191, 36, 0.6))',
          borderRadius: '2px',
        }"
      />
    </div>
  </div>
</template>
