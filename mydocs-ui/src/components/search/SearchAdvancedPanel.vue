<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSearchStore } from '@/stores/search'
import { getIndices } from '@/api/search'
import type { VectorIndexInfo } from '@/types'

const searchStore = useSearchStore()
const indices = ref<VectorIndexInfo[]>([])

onMounted(async () => {
  try {
    const resp = await getIndices()
    indices.value = [...resp.pages, ...resp.documents]
  } catch { /* ignore */ }
})
</script>

<template>
  <div
    class="rounded-lg border p-4 space-y-4"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
  >
    <h3 class="text-sm font-semibold" style="color: var(--color-text-primary);">Advanced Search Options</h3>

    <!-- Mode selector -->
    <div>
      <label class="block text-xs font-medium mb-1.5" style="color: var(--color-text-secondary);">Search Mode</label>
      <div class="flex gap-2">
        <label
          v-for="mode in (['fulltext', 'vector', 'hybrid'] as const)"
          :key="mode"
          class="flex items-center gap-1.5 text-sm cursor-pointer"
          style="color: var(--color-text-primary);"
        >
          <input type="radio" :value="mode" v-model="searchStore.searchMode" class="accent-blue-600" />
          {{ mode.charAt(0).toUpperCase() + mode.slice(1) }}
        </label>
      </div>
    </div>

    <!-- Top K and Min Score -->
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Top K</label>
        <input
          v-model.number="searchStore.config.top_k"
          type="number"
          min="1"
          max="100"
          class="w-full rounded-lg border px-3 py-2 text-sm"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        />
      </div>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Min Score</label>
        <input
          v-model.number="searchStore.config.min_score"
          type="number"
          min="0"
          max="1"
          step="0.1"
          class="w-full rounded-lg border px-3 py-2 text-sm"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        />
      </div>
    </div>

    <!-- Fulltext config -->
    <div v-if="searchStore.searchMode === 'fulltext' || searchStore.searchMode === 'hybrid'">
      <h4 class="text-xs font-semibold mb-2" style="color: var(--color-text-secondary);">Fulltext Options</h4>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs mb-1" style="color: var(--color-text-secondary);">Score Boost</label>
          <input
            v-model.number="searchStore.config.fulltext!.score_boost"
            type="number"
            step="0.1"
            class="w-full rounded border px-2 py-1.5 text-sm"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          />
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-1.5 text-xs" style="color: var(--color-text-primary);">
            <input type="checkbox" v-model="searchStore.config.fulltext!.fuzzy!.enabled" class="rounded" />
            Fuzzy matching
          </label>
        </div>
      </div>
    </div>

    <!-- Vector config -->
    <div v-if="searchStore.searchMode === 'vector' || searchStore.searchMode === 'hybrid'">
      <h4 class="text-xs font-semibold mb-2" style="color: var(--color-text-secondary);">Vector Options</h4>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs mb-1" style="color: var(--color-text-secondary);">Index</label>
          <select
            v-model="searchStore.config.vector!.index_name"
            class="w-full rounded border px-2 py-1.5 text-sm"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          >
            <option :value="undefined">Auto</option>
            <option v-for="idx in indices" :key="idx.index_name" :value="idx.index_name">
              {{ idx.index_name }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs mb-1" style="color: var(--color-text-secondary);">Num Candidates</label>
          <input
            v-model.number="searchStore.config.vector!.num_candidates"
            type="number"
            class="w-full rounded border px-2 py-1.5 text-sm"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          />
        </div>
      </div>
    </div>

    <!-- Hybrid config -->
    <div v-if="searchStore.searchMode === 'hybrid'">
      <h4 class="text-xs font-semibold mb-2" style="color: var(--color-text-secondary);">Hybrid Options</h4>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs mb-1" style="color: var(--color-text-secondary);">Method</label>
          <select
            v-model="searchStore.config.hybrid!.combination_method"
            class="w-full rounded border px-2 py-1.5 text-sm"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          >
            <option value="rrf">RRF</option>
            <option value="weighted_sum">Weighted Sum</option>
          </select>
        </div>
        <div>
          <label class="block text-xs mb-1" style="color: var(--color-text-secondary);">RRF K</label>
          <input
            v-model.number="searchStore.config.hybrid!.rrf_k"
            type="number"
            class="w-full rounded border px-2 py-1.5 text-sm"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          />
        </div>
      </div>
    </div>
  </div>
</template>
