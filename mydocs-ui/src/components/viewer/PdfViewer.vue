<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'

const props = defineProps<{
  fileUrl: string
  page: number
  zoom: number
}>()

const canvasRef = ref<HTMLCanvasElement>()
const pdfDoc = ref<any>(null)
const rendering = ref(false)

async function loadPdf() {
  const pdfjsLib = await import('pdfjs-dist')
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString()

  const loadingTask = pdfjsLib.getDocument(props.fileUrl)
  pdfDoc.value = await loadingTask.promise
  renderPage()
}

async function renderPage() {
  if (!pdfDoc.value || !canvasRef.value || rendering.value) return
  rendering.value = true

  try {
    const page = await pdfDoc.value.getPage(props.page)
    const viewport = page.getViewport({ scale: props.zoom * 1.5 })
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')!
    canvas.height = viewport.height
    canvas.width = viewport.width

    await page.render({ canvasContext: ctx, viewport }).promise
  } finally {
    rendering.value = false
  }
}

onMounted(loadPdf)
watch(() => [props.page, props.zoom], renderPage)
</script>

<template>
  <div class="h-full overflow-auto flex justify-center p-4" style="background-color: var(--color-bg-tertiary);">
    <canvas ref="canvasRef" class="shadow-lg" style="background: white;" />
  </div>
</template>
