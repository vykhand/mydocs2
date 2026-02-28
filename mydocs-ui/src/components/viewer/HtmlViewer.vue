<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  content: string
}>()

const showRaw = ref(false)
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-end px-3 py-1.5 shrink-0" style="border-bottom: 1px solid var(--color-border);">
      <label class="flex items-center gap-1.5 text-xs cursor-pointer" style="color: var(--color-text-secondary);">
        <input type="checkbox" v-model="showRaw" class="rounded" />
        Raw
      </label>
    </div>
    <div class="flex-1 overflow-auto p-4">
      <div v-if="showRaw" class="whitespace-pre-wrap font-mono text-xs leading-relaxed" style="color: var(--color-text-primary);">{{ content || 'No content available.' }}</div>
      <div v-else class="html-content" style="color: var(--color-text-primary);" v-html="content || '<p style=\'color: var(--color-text-secondary)\'>No content available.</p>'" />
    </div>
  </div>
</template>

<style scoped>
.html-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}
.html-content :deep(th),
.html-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 0.375rem 0.5rem;
  text-align: left;
  font-size: 0.8rem;
}
.html-content :deep(th) {
  background: var(--color-bg-tertiary);
  font-weight: 600;
}
.html-content :deep(p) {
  margin: 0.375rem 0;
  line-height: 1.5;
  font-size: 0.875rem;
}
</style>
