<script setup lang="ts">
import { ref, watch, computed } from 'vue'
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

const { pdf, pages: pdfPages } = usePDF(computed(() => props.fileUrl))

watch(pdfPages, (total) => {
  if (total) emit('totalPagesResolved', total)
})

const currentPage = computed(() => Math.min(Math.max(1, props.page), pdfPages.value || 1))
</script>

<template>
  <div ref="containerRef" class="h-full w-full overflow-auto relative" style="background-color: var(--color-bg-tertiary);">
    <div class="flex justify-center py-2">
      <div class="relative inline-block">
        <VuePDF
          :pdf="pdf"
          :page="currentPage"
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
