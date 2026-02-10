<script setup lang="ts">
import type { Document } from '@/types'
import { getDocumentFileUrl } from '@/api/documents'
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut,
  Maximize2, Download, X,
} from 'lucide-vue-next'

const props = defineProps<{
  currentPage: number
  totalPages: number
  zoom: number
  document: Document | null
}>()

const emit = defineEmits<{
  goToPage: [page: number]
  prevPage: []
  nextPage: []
  setZoom: [zoom: number]
  fitWidth: []
  fitPage: []
  close: []
}>()

function enterFullscreen() {
  document.documentElement.requestFullscreen?.()
}
</script>

<template>
  <div
    class="flex items-center justify-between px-4 py-2 border-b shrink-0"
    style="background-color: var(--color-bg-secondary); border-color: var(--color-border);"
  >
    <!-- Left: page nav -->
    <div class="flex items-center gap-2">
      <button @click="emit('prevPage')" :disabled="currentPage <= 1" class="p-1.5 rounded disabled:opacity-30" style="color: var(--color-text-secondary);">
        <ChevronLeft :size="18" />
      </button>
      <span class="text-sm" style="color: var(--color-text-primary);">
        <input
          type="number"
          :value="currentPage"
          @change="emit('goToPage', Number(($event.target as HTMLInputElement).value))"
          class="w-12 text-center rounded border px-1 py-0.5 text-sm"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          :min="1"
          :max="totalPages"
        />
        / {{ totalPages }}
      </span>
      <button @click="emit('nextPage')" :disabled="currentPage >= totalPages" class="p-1.5 rounded disabled:opacity-30" style="color: var(--color-text-secondary);">
        <ChevronRight :size="18" />
      </button>
    </div>

    <!-- Center: zoom -->
    <div class="flex items-center gap-1.5">
      <button @click="emit('setZoom', zoom - 0.25)" class="p-1.5 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
        <ZoomOut :size="18" />
      </button>
      <span class="text-xs w-12 text-center" style="color: var(--color-text-secondary);">{{ Math.round(zoom * 100) }}%</span>
      <button @click="emit('setZoom', zoom + 0.25)" class="p-1.5 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
        <ZoomIn :size="18" />
      </button>
      <button @click="emit('fitWidth')" class="p-1.5 rounded hover:opacity-70" style="color: var(--color-text-secondary);" title="Fit to width">
        <Maximize2 :size="18" />
      </button>
    </div>

    <!-- Right: actions -->
    <div class="flex items-center gap-1.5">
      <a
        v-if="document"
        :href="getDocumentFileUrl(document.id)"
        download
        class="p-1.5 rounded hover:opacity-70"
        style="color: var(--color-text-secondary);"
        title="Download"
      >
        <Download :size="18" />
      </a>
      <button @click="enterFullscreen" class="p-1.5 rounded hover:opacity-70" style="color: var(--color-text-secondary);" title="Fullscreen">
        <Maximize2 :size="18" />
      </button>
      <button @click="emit('close')" class="p-1.5 rounded hover:opacity-70" style="color: var(--color-text-secondary);" title="Close">
        <X :size="18" />
      </button>
    </div>
  </div>
</template>
