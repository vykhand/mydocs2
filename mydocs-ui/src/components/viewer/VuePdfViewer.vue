<script setup lang="ts">
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue'
import { VuePDF, usePDF } from '@tato30/vue-pdf'

const props = defineProps<{
  fileUrl: string
  page: number
  highlightQuery?: string
}>()

const emit = defineEmits<{
  totalPagesResolved: [total: number]
}>()

const containerRef = ref<HTMLDivElement>()
const vuePDFRef = ref<InstanceType<typeof VuePDF>>()

const { pdf, pages: pdfPages } = usePDF(computed(() => props.fileUrl))

watch(pdfPages, (total) => {
  if (total) emit('totalPagesResolved', total)
})

const currentPage = computed(() => Math.min(Math.max(1, props.page), pdfPages.value || 1))

// Debounced resize observer to reload PDF when container width changes
let resizeTimer: ReturnType<typeof setTimeout> | undefined
let resizeObserver: ResizeObserver | undefined

onMounted(() => {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        vuePDFRef.value?.reload()
      }, 200)
    })
    resizeObserver.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  clearTimeout(resizeTimer)
  resizeObserver?.disconnect()
})
</script>

<template>
  <div ref="containerRef" class="h-full w-full overflow-auto relative" style="background-color: var(--color-bg-tertiary);">
    <div class="flex justify-center py-2">
      <div class="relative w-full px-2">
        <VuePDF
          ref="vuePDFRef"
          :pdf="pdf"
          :page="currentPage"
          fit-parent
          text-layer
          annotation-layer
          :highlight-text="highlightQuery || undefined"
        />
        <!-- Annotation overlay layer for future extraction result annotations -->
        <div class="absolute inset-0 pointer-events-none" data-annotation-overlay />
      </div>
    </div>
  </div>
</template>
