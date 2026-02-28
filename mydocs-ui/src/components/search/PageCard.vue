<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SearchResult } from '@/types'
import { getPageImageUrl } from '@/api/documents'
import { useAppStore } from '@/stores/app'
import { FileText } from 'lucide-vue-next'

const props = defineProps<{
  result: SearchResult
  query?: string
}>()

const appStore = useAppStore()

const thumbError = ref(false)
const thumbLoaded = ref(false)

const thumbnailUrl = computed(() => {
  if (!props.result.document_id || !props.result.page_number) return ''
  return getPageImageUrl(props.result.document_id, props.result.page_number, 200)
})

const scorePercent = computed(() => Math.round(props.result.score * 100))

const snippet = computed(() => {
  const text = props.result.content_markdown || props.result.content || ''
  return text.slice(0, 150)
})

function openResult() {
  const pageNum = props.result.page_number || 1
  appStore.openViewer(props.result.document_id, pageNum, props.query || '', 'page')
}

function onThumbLoad() {
  thumbLoaded.value = true
  thumbError.value = false
}

function onThumbError() {
  thumbError.value = true
  thumbLoaded.value = false
}
</script>

<template>
  <div
    class="relative group rounded-lg border overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="openResult"
  >
    <!-- Thumbnail -->
    <div
      class="w-full aspect-[4/3] flex items-center justify-center overflow-hidden relative"
      style="background-color: var(--color-bg-tertiary);"
    >
      <img
        v-if="thumbnailUrl && !thumbError"
        :src="thumbnailUrl"
        class="w-full h-full object-cover"
        :class="{ 'opacity-0': !thumbLoaded }"
        loading="lazy"
        @load="onThumbLoad"
        @error="onThumbError"
      />
      <FileText v-if="thumbError || !thumbLoaded" :size="36" style="color: var(--color-text-secondary);" :class="{ 'absolute': !thumbError && !thumbLoaded }" />

      <!-- Page badge -->
      <span
        v-if="result.page_number"
        class="absolute top-2 right-2 px-1.5 py-0.5 rounded text-xs font-medium"
        style="background-color: var(--color-accent); color: white;"
      >
        Page {{ result.page_number }}
      </span>

      <!-- Score badge -->
      <span
        class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-xs font-medium"
        style="background-color: var(--color-bg-secondary); color: var(--color-text-primary); opacity: 0.9;"
      >
        {{ scorePercent }}%
      </span>
    </div>

    <!-- Info -->
    <div class="p-3">
      <p class="text-xs font-medium truncate" style="color: var(--color-text-primary);">
        {{ result.file_name || 'Unknown document' }}
      </p>
      <p class="text-xs mt-1 line-clamp-2" style="color: var(--color-text-secondary);">
        {{ snippet }}
      </p>
      <div class="flex flex-wrap gap-1 mt-1.5" v-if="result.tags?.length">
        <span
          v-for="tag in result.tags.slice(0, 2)"
          :key="tag"
          class="px-1.5 py-0.5 rounded text-xs"
          style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
        >
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>
