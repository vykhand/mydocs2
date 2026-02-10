<script setup lang="ts">
import { useSearchStore } from '@/stores/search'
import { Search } from 'lucide-vue-next'

const searchStore = useSearchStore()

function onSubmit() {
  searchStore.executeSearch()
}
</script>

<template>
  <form @submit.prevent="onSubmit" class="relative">
    <Search
      :size="20"
      class="absolute left-4 top-1/2 -translate-y-1/2"
      style="color: var(--color-text-secondary);"
    />
    <input
      v-model="searchStore.query"
      placeholder="Search documents..."
      class="w-full pl-12 pr-4 py-4 rounded-xl border text-base"
      style="background-color: var(--color-bg-secondary); border-color: var(--color-border); color: var(--color-text-primary);"
      @keydown.enter="onSubmit"
    />
  </form>
</template>
