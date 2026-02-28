<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { useDocumentsStore } from '@/stores/documents'
import { LayoutGrid, List } from 'lucide-vue-next'

defineProps<{
  resultCount: number
}>()

const appStore = useAppStore()
const docsStore = useDocumentsStore()

const allSelected = () => docsStore.documents.length > 0 && docsStore.documents.every(d => docsStore.selectedIds.has(d.id))

function toggleAll() {
  if (allSelected()) {
    docsStore.clearSelection()
  } else {
    docsStore.selectAll()
  }
}
</script>

<template>
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <!-- Select all checkbox (grid mode) -->
      <label v-if="appStore.galleryViewMode === 'grid'" class="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" :checked="allSelected()" @change="toggleAll" class="rounded" />
        <span class="text-xs" style="color: var(--color-text-secondary);">Select all</span>
      </label>
      <p class="text-sm" style="color: var(--color-text-secondary);">
        {{ resultCount }} {{ resultCount === 1 ? 'result' : 'results' }}
      </p>
    </div>
    <div class="flex items-center gap-1">
      <button
        @click="appStore.galleryViewMode = 'grid'"
        class="p-1.5 rounded"
        :style="{
          color: appStore.galleryViewMode === 'grid' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          backgroundColor: appStore.galleryViewMode === 'grid' ? 'var(--color-bg-tertiary)' : 'transparent',
        }"
        title="Grid view"
      >
        <LayoutGrid :size="18" />
      </button>
      <button
        @click="appStore.galleryViewMode = 'list'"
        class="p-1.5 rounded"
        :style="{
          color: appStore.galleryViewMode === 'list' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          backgroundColor: appStore.galleryViewMode === 'list' ? 'var(--color-bg-tertiary)' : 'transparent',
        }"
        title="List view"
      >
        <List :size="18" />
      </button>
    </div>
  </div>
</template>
