<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMarkdownRenderer } from '@/composables/useMarkdownRenderer'

const props = defineProps<{
  content: string
}>()

const emit = defineEmits<{
  goToPage: [page: number]
}>()

const showRaw = ref(false)
const { render } = useMarkdownRenderer()

const renderedHtml = computed(() => render(props.content))

function handleClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const link = target.closest('a')
  if (link) {
    const href = link.getAttribute('href') || ''
    const pageMatch = href.match(/^#page[_-]?(\d+)$/i)
    if (pageMatch) {
      e.preventDefault()
      emit('goToPage', parseInt(pageMatch[1], 10))
    }
  }
}
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center gap-2 px-4 py-2 border-b shrink-0" style="border-color: var(--color-border);">
      <button
        @click="showRaw = false"
        class="px-2 py-1 text-xs rounded"
        :style="{
          backgroundColor: !showRaw ? 'var(--color-bg-tertiary)' : 'transparent',
          color: !showRaw ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        }"
      >Rendered</button>
      <button
        @click="showRaw = true"
        class="px-2 py-1 text-xs rounded"
        :style="{
          backgroundColor: showRaw ? 'var(--color-bg-tertiary)' : 'transparent',
          color: showRaw ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        }"
      >Raw</button>
    </div>
    <div class="flex-1 overflow-auto p-4">
      <pre v-if="showRaw" class="text-xs whitespace-pre-wrap font-mono" style="color: var(--color-text-primary);">{{ content }}</pre>
      <div
        v-else
        class="prose prose-sm max-w-none dark:prose-invert"
        style="color: var(--color-text-primary);"
        v-html="renderedHtml"
        @click="handleClick"
      />
    </div>
  </div>
</template>
