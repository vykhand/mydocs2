<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const showRaw = ref(false)

// Simple markdown-to-HTML conversion for display
// Handles headings, bold, italic, code blocks, lists, links, and paragraphs
const renderedHtml = computed(() => {
  if (!props.content) return '<p style="color: var(--color-text-secondary)">No content available.</p>'

  let html = props.content
    // Escape HTML entities first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Code blocks (triple backtick)
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    // Headings
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // Line breaks (double newline = paragraph break)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines
    .replace(/\n/g, '<br>')

  return `<p>${html}</p>`
})
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
      <div v-else class="markdown-content prose prose-sm max-w-none" style="color: var(--color-text-primary);" v-html="renderedHtml" />
    </div>
  </div>
</template>

<style scoped>
.markdown-content :deep(h1) { font-size: 1.5rem; font-weight: 600; margin: 1rem 0 0.5rem; }
.markdown-content :deep(h2) { font-size: 1.25rem; font-weight: 600; margin: 0.75rem 0 0.5rem; }
.markdown-content :deep(h3) { font-size: 1.1rem; font-weight: 600; margin: 0.5rem 0 0.25rem; }
.markdown-content :deep(p) { margin: 0.5rem 0; line-height: 1.6; }
.markdown-content :deep(strong) { font-weight: 600; }
.markdown-content :deep(a) { color: var(--color-accent); text-decoration: underline; }
.markdown-content :deep(.code-block) {
  background: var(--color-bg-tertiary);
  border-radius: 6px;
  padding: 0.75rem;
  overflow-x: auto;
  font-size: 0.8rem;
  margin: 0.5rem 0;
}
.markdown-content :deep(.inline-code) {
  background: var(--color-bg-tertiary);
  border-radius: 3px;
  padding: 0.1rem 0.3rem;
  font-size: 0.85em;
}
</style>
