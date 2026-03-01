<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import type { SearchResult } from '@/types'
import { getPageThumbnailUrl } from '@/api/documents'
import { FileText } from 'lucide-vue-next'

const props = defineProps<{
  result: SearchResult
}>()

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const thumbnailUrl = computed(() =>
  props.result.document_id && props.result.page_number
    ? getPageThumbnailUrl(props.result.document_id, props.result.page_number, 600)
    : ''
)

const scorePct = computed(() => Math.round(props.result.score * 100))

const snippet = computed(() => {
  const text = props.result.content_markdown || props.result.content || ''
  return text.length > 200 ? text.substring(0, 200) + '...' : text
})

function handleClick() {
  appStore.openViewer(
    props.result.document_id,
    props.result.page_number || 1,
    (route.query.q as string) || '',
    'page'
  )
  router.push(`/doc/${props.result.document_id}?page=${props.result.page_number || 1}&mode=page&highlight=${encodeURIComponent((route.query.q as string) || '')}`)
}
</script>

<template>
  <div
    class="rounded-lg border cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="handleClick"
  >
    <!-- Thumbnail -->
    <div class="w-full h-48 overflow-hidden relative" style="background-color: var(--color-bg-tertiary);">
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        class="w-full h-full object-contain object-top"
        loading="lazy"
        @error="($event.target as HTMLImageElement).style.display = 'none'"
      />
      <div class="w-full h-full flex items-center justify-center">
        <FileText :size="24" style="color: var(--color-text-secondary); opacity: 0.3;" />
      </div>
      <!-- Page number badge -->
      <span
        v-if="result.page_number != null"
        class="absolute top-2 left-2 text-xs px-1.5 py-0.5 rounded font-medium"
        style="background-color: rgba(0,0,0,0.6); color: white;"
      >
        p.{{ result.page_number }}
      </span>
      <!-- Score badge -->
      <span
        class="absolute top-2 right-2 text-xs px-1.5 py-0.5 rounded-full font-medium"
        style="background-color: var(--color-bg-tertiary); color: var(--color-accent);"
      >
        {{ scorePct }}%
      </span>
    </div>

    <!-- Content -->
    <div class="p-3">
      <p class="text-xs font-medium truncate" style="color: var(--color-text-primary);">
        {{ result.file_name || 'Unknown' }}
      </p>
      <p class="text-xs mt-1 line-clamp-3" style="color: var(--color-text-secondary);">
        {{ snippet }}
      </p>
      <div v-if="result.tags?.length" class="flex flex-wrap gap-1 mt-2">
        <span
          v-for="tag in result.tags.slice(0, 2)"
          :key="tag"
          class="px-1 py-0.5 rounded text-[10px]"
          style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
        >
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>
