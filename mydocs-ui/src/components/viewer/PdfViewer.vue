<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

const props = defineProps<{
  fileUrl: string
  page: number
  zoom: number
}>()

const canvasRef = ref<HTMLCanvasElement>()
const pdfDoc = ref<any>(null)
const rendering = ref(false)
const pendingRender = ref(false)

async function loadPdf() {
  if (!props.fileUrl) return
  try {
    const loadingTask = pdfjsLib.getDocument(props.fileUrl)
    pdfDoc.value = await loadingTask.promise
    await renderPage()
  } catch (err) {
    console.error('Failed to load PDF:', err)
  }
}

async function renderPage() {
  if (!pdfDoc.value || !canvasRef.value) return

  if (rendering.value) {
    pendingRender.value = true
    return
  }

  rendering.value = true
  try {
    const pageNum = Math.min(Math.max(1, props.page), pdfDoc.value.numPages)
    const page = await pdfDoc.value.getPage(pageNum)
    const viewport = page.getViewport({ scale: props.zoom * 1.5 })
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')!
    canvas.height = viewport.height
    canvas.width = viewport.width

    await page.render({ canvasContext: ctx, viewport }).promise
  } catch (err) {
    console.error('Failed to render page:', err)
  } finally {
    rendering.value = false
    if (pendingRender.value) {
      pendingRender.value = false
      await renderPage()
    }
  }
}

onMounted(loadPdf)

watch(() => props.fileUrl, () => {
  pdfDoc.value = null
  loadPdf()
})

watch(() => [props.page, props.zoom], () => {
  renderPage()
})
</script>

<template>
  <div class="h-full overflow-auto flex justify-center p-4" style="background-color: var(--color-bg-tertiary);">
    <canvas ref="canvasRef" class="shadow-lg" style="background: white;" />
  </div>
</template>
