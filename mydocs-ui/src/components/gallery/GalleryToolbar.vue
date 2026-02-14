<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { LayoutGrid, List } from 'lucide-vue-next'

defineProps<{
  resultCount: number
}>()

const appStore = useAppStore()
</script>

<template>
  <div class="flex items-center justify-between">
    <p class="text-sm" style="color: var(--color-text-secondary);">
      {{ resultCount }} {{ resultCount === 1 ? 'result' : 'results' }}
    </p>
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
