<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMarkdownRenderer } from '@/composables/useMarkdownRenderer'

const props = withDefaults(defineProps<{
  content: string
  pageCount?: number
}>(), {
  pageCount: 0,
})

const emit = defineEmits<{
  goToPage: [page: number]
}>()

const showRaw = ref(false)
const pageJumpInput = ref('')
const { render } = useMarkdownRenderer()

const renderedHtml = computed(() => render(props.content))

function handlePageJump() {
  const page = parseInt(pageJumpInput.value, 10)
  if (page >= 1 && page <= props.pageCount) {
    emit('goToPage', page)
    pageJumpInput.value = ''
  }
}

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
      <!-- Page navigation links -->
      <div
        v-if="pageCount > 0 && !showRaw"
        class="mb-4 pb-3 border-b"
        style="border-color: var(--color-border);"
      >
        <p class="text-xs font-medium mb-2" style="color: var(--color-text-secondary);">Page Navigation</p>
        <!-- Compact links for ≤ 20 pages -->
        <div v-if="pageCount <= 20" class="flex flex-wrap gap-1">
          <a
            v-for="p in pageCount"
            :key="p"
            :href="`#page_${p}`"
            class="px-1.5 py-0.5 text-xs rounded hover:opacity-80 transition-opacity"
            style="background-color: var(--color-bg-tertiary); color: var(--color-accent);"
            @click.prevent="emit('goToPage', p)"
          >{{ p }}</a>
        </div>
        <!-- Page input for > 20 pages -->
        <div v-else class="flex items-center gap-2">
          <span class="text-xs" style="color: var(--color-text-secondary);">{{ pageCount }} pages — go to:</span>
          <input
            v-model="pageJumpInput"
            type="number"
            min="1"
            :max="pageCount"
            placeholder="#"
            class="w-16 px-2 py-0.5 text-xs rounded border"
            style="border-color: var(--color-border); background-color: var(--color-bg-tertiary); color: var(--color-text-primary);"
            @keyup.enter="handlePageJump"
          />
          <button
            class="px-2 py-0.5 text-xs rounded"
            style="background-color: var(--color-accent); color: white;"
            @click="handlePageJump"
          >Go</button>
        </div>
      </div>

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
