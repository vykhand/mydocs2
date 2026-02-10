<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import type { SearchResult } from '@/types'
import ScoreBreakdown from './ScoreBreakdown.vue'
import { FileText, Eye } from 'lucide-vue-next'

const props = defineProps<{
  result: SearchResult
}>()

const router = useRouter()
const appStore = useAppStore()

const scorePct = computed(() => Math.round(props.result.score * 100))

const snippet = computed(() => {
  const text = props.result.content_markdown || props.result.content || ''
  return text.length > 300 ? text.substring(0, 300) + '...' : text
})
</script>

<template>
  <div
    class="rounded-lg border p-4 cursor-pointer hover:shadow-sm transition-shadow"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="router.push(`/documents/${result.document_id}`)"
  >
    <div class="flex items-start justify-between gap-3 mb-2">
      <div class="flex items-center gap-2">
        <FileText :size="16" style="color: var(--color-text-secondary);" />
        <span class="text-sm font-medium" style="color: var(--color-text-primary);">
          {{ result.file_name || 'Unknown' }}
        </span>
        <span v-if="result.page_number != null" class="text-xs px-1.5 py-0.5 rounded" style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);">
          Page {{ result.page_number }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <div class="text-xs font-medium px-2 py-0.5 rounded-full" style="background-color: var(--color-bg-tertiary); color: var(--color-accent);">
          {{ scorePct }}%
        </div>
        <button
          v-if="result.page_number != null"
          @click.stop="router.push(`/documents/${result.document_id}/view?page=${result.page_number}`)"
          class="p-1 rounded hover:opacity-70"
          style="color: var(--color-accent);"
          title="View in context"
        >
          <Eye :size="16" />
        </button>
      </div>
    </div>

    <!-- Score bar -->
    <div class="w-full h-1.5 rounded-full mb-3" style="background-color: var(--color-bg-tertiary);">
      <div
        class="h-full rounded-full"
        style="background-color: var(--color-accent);"
        :style="{ width: scorePct + '%' }"
      />
    </div>

    <!-- Snippet -->
    <p class="text-sm leading-relaxed" style="color: var(--color-text-secondary);">{{ snippet }}</p>

    <!-- Tags -->
    <div v-if="result.tags?.length" class="flex flex-wrap gap-1 mt-2">
      <span
        v-for="tag in result.tags"
        :key="tag"
        class="px-1.5 py-0.5 rounded text-xs"
        style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
      >
        {{ tag }}
      </span>
    </div>

    <!-- Advanced: Score Breakdown -->
    <ScoreBreakdown v-if="appStore.mode === 'advanced'" :scores="result.scores" :total="result.score" class="mt-3" />
  </div>
</template>
