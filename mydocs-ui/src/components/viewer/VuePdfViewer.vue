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
  pdfPageDimensions: [dims: { width: number; height: number }]
}>()

const containerRef = ref<HTMLDivElement>()
const vuePDFRef = ref<InstanceType<typeof VuePDF>>()

const { pdf, pages: pdfPages } = usePDF(computed(() => props.fileUrl))

watch(pdfPages, (total) => {
  if (total) emit('totalPagesResolved', total)
})

const currentPage = computed(() => Math.min(Math.max(1, props.page), pdfPages.value || 1))

// Emit native page dimensions from pdfjs when page is rendered
function onPdfLoaded(viewport: { width: number; height: number; scale: number }) {
  if (viewport && viewport.scale) {
    emit('pdfPageDimensions', {
      width: viewport.width / viewport.scale / 72,
      height: viewport.height / viewport.scale / 72,
    })
  }
}

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
          @loaded="onPdfLoaded"
        >
          <template #overlay="{ width, height }">
            <!-- Wrapper with explicit pixel dimensions matching the rendered canvas.
                 VuePDF's .page container sizes from ALL children (text/annotation layers
                 are in normal flow, not absolutely positioned), so inset-0 on the overlay
                 would be larger than the canvas. This wrapper constrains the overlay to
                 the exact canvas area. -->
            <div
              v-if="width && height"
              class="absolute top-0 left-0 pointer-events-none"
              :style="{ width: Math.floor(width) + 'px', height: Math.floor(height) + 'px' }"
            >
              <slot name="page-overlay" :width="width" :height="height" />
            </div>
          </template>
        </VuePDF>
      </div>
    </div>
  </div>
</template>
