<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import PageResultCard from './PageResultCard.vue'
import SearchResultCard from './SearchResultCard.vue'
import type { SearchResult } from '@/types'

defineProps<{
  results: SearchResult[]
}>()

const appStore = useAppStore()
</script>

<template>
  <!-- Grid mode: page cards with thumbnails -->
  <div v-if="appStore.galleryViewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
    <PageResultCard
      v-for="result in results"
      :key="result.id"
      :result="result"
    />
  </div>

  <!-- List mode: detailed result cards -->
  <div v-else class="space-y-3">
    <SearchResultCard
      v-for="result in results"
      :key="result.id"
      :result="result"
    />
  </div>
</template>
