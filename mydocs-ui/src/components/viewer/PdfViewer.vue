<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'

const props = defineProps<{
  fileUrl: string
  page: number
  zoom: number
  highlightQuery?: string
}>()

const emit = defineEmits<{
  totalPagesResolved: [total: number]
}>()

const loading = ref(true)
const error = ref<string | null>(null)
const pdfRef = ref<InstanceType<typeof VuePdfEmbed> | null>(null)

const scale = computed(() => props.zoom)

function handleLoaded(pdfProxy: any) {
  loading.value = false
  error.value = null
  if (pdfProxy?.numPages) {
    emit('totalPagesResolved', pdfProxy.numPages)
  }
}

function handleError(err: any) {
  loading.value = false
  error.value = err?.message || 'Failed to load PDF'
  console.error('PDF load error:', err)
}

function handleProgress() {
  loading.value = true
  error.value = null
}

watch(() => props.fileUrl, () => {
  loading.value = true
  error.value = null
})
</script>

<template>
  <div class="h-full w-full overflow-auto" style="background-color: var(--color-bg-tertiary);">
    <div v-if="loading" class="flex items-center justify-center h-32">
      <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
    </div>
    <div v-if="error" class="flex flex-col items-center justify-center h-full gap-2 p-4">
      <p class="text-sm font-medium" style="color: var(--color-danger);">PDF Error</p>
      <p class="text-xs text-center max-w-[300px]" style="color: var(--color-text-secondary);">{{ error }}</p>
    </div>
    <div v-show="!error" class="pdf-embed-container">
      <VuePdfEmbed
        ref="pdfRef"
        :source="fileUrl"
        :page="page"
        :scale="scale"
        :text-layer="true"
        :annotation-layer="true"
        @loaded="handleLoaded"
        @loading-failed="handleError"
        @progress="handleProgress"
      />
    </div>
  </div>
</template>

<style scoped>
.pdf-embed-container {
  display: flex;
  justify-content: center;
  min-height: 100%;
}

.pdf-embed-container :deep(.vue-pdf-embed > div) {
  margin: 0 auto;
}

/* Highlight styling for text layer search matches */
.pdf-embed-container :deep(mark) {
  background: var(--color-highlight, rgba(251, 191, 36, 0.4));
  color: transparent;
  border-radius: 2px;
  padding: 1px 0;
}
</style>
