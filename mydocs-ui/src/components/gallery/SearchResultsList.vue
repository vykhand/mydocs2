<script setup lang="ts">
import SearchResultCard from '@/components/search/SearchResultCard.vue'
import type { SearchResult } from '@/types'

defineProps<{
  results: SearchResult[]
}>()
</script>

<template>
  <div class="space-y-3">
    <SearchResultCard
      v-for="result in results"
      :key="result.id"
      :result="result"
    />
  </div>
</template>
