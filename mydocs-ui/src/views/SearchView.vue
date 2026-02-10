<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useSearchStore } from '@/stores/search'
import SearchBar from '@/components/search/SearchBar.vue'
import SearchFilters from '@/components/search/SearchFilters.vue'
import SearchAdvancedPanel from '@/components/search/SearchAdvancedPanel.vue'
import SearchResultCard from '@/components/search/SearchResultCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import { Search } from 'lucide-vue-next'

const appStore = useAppStore()
const searchStore = useSearchStore()

const isAdvanced = computed(() => appStore.mode === 'advanced')
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <SearchBar />

    <!-- Target toggle -->
    <div class="flex items-center justify-center gap-2">
      <button
        v-for="target in (['pages', 'documents'] as const)"
        :key="target"
        @click="searchStore.searchTarget = target"
        class="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
        :style="{
          backgroundColor: searchStore.searchTarget === target ? 'var(--color-accent)' : 'var(--color-bg-tertiary)',
          color: searchStore.searchTarget === target ? '#fff' : 'var(--color-text-secondary)',
        }"
      >
        {{ target === 'pages' ? 'Pages' : 'Documents' }}
      </button>
    </div>

    <SearchFilters />
    <SearchAdvancedPanel v-if="isAdvanced" />

    <!-- Results -->
    <LoadingSkeleton v-if="searchStore.loading" :lines="6" />

    <div v-else-if="searchStore.response" class="space-y-3">
      <p class="text-sm" style="color: var(--color-text-secondary);">
        {{ searchStore.response.total }} result(s) &middot; {{ searchStore.response.search_mode }} search
      </p>
      <SearchResultCard
        v-for="result in searchStore.response.results"
        :key="result.id"
        :result="result"
      />
      <EmptyState
        v-if="searchStore.response.results.length === 0"
        :icon="Search"
        title="No results"
        description="Try adjusting your search query or filters."
      />
    </div>

    <EmptyState
      v-else
      :icon="Search"
      title="Search documents"
      description="Enter a query above to search across your document library."
    />
  </div>
</template>
