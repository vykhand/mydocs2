<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { getDocument, GlobalWorkerOptions, TextLayer } from 'pdfjs-dist'
// Vite resolves ?url imports to the hashed asset path at build time
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

const props = defineProps<{
  fileUrl: string
  page: number
  zoom: number
  highlightQuery?: string
}>()

const emit = defineEmits<{
  totalPagesResolved: [total: number]
}>()

const canvasRef = ref<HTMLCanvasElement>()
const textLayerRef = ref<HTMLDivElement>()
const containerRef = ref<HTMLDivElement>()

const loading = ref(false)
const error = ref<string | null>(null)

let pdfDoc: any = null
let currentTextLayer: any = null
let rendering = false
let pendingRender = false

async function loadPdf() {
  if (!props.fileUrl) return
  error.value = null
  loading.value = true

  // Clean up previous document
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }

  try {
    const response = await fetch(props.fileUrl)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    const data = await response.arrayBuffer()
    pdfDoc = await getDocument({ data }).promise
    emit('totalPagesResolved', pdfDoc.numPages)
    await renderPage()
  } catch (err: any) {
    console.error('Failed to load PDF:', err)
    error.value = err?.message || 'Failed to load PDF'
  } finally {
    loading.value = false
  }
}

async function renderPage() {
  if (!pdfDoc || !canvasRef.value || !textLayerRef.value) return

  if (rendering) {
    pendingRender = true
    return
  }

  rendering = true

  try {
    const pageNum = Math.min(Math.max(1, props.page), pdfDoc.numPages)
    const page = await pdfDoc.getPage(pageNum)

    const scale = props.zoom * (window.devicePixelRatio || 1)
    const viewport = page.getViewport({ scale: props.zoom })
    const renderViewport = page.getViewport({ scale })

    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')!

    // Set canvas dimensions for high-DPI rendering
    canvas.width = renderViewport.width
    canvas.height = renderViewport.height
    canvas.style.width = viewport.width + 'px'
    canvas.style.height = viewport.height + 'px'

    // Render canvas
    await page.render({ canvasContext: ctx, viewport: renderViewport }).promise

    // Clear previous text layer
    if (currentTextLayer) {
      currentTextLayer.cancel()
      currentTextLayer = null
    }
    const textLayerDiv = textLayerRef.value
    textLayerDiv.innerHTML = ''
    textLayerDiv.style.width = viewport.width + 'px'
    textLayerDiv.style.height = viewport.height + 'px'

    // Render text layer
    const textContent = await page.getTextContent()

    currentTextLayer = new TextLayer({
      textContentSource: textContent,
      container: textLayerDiv,
      viewport,
    })

    await currentTextLayer.render()

    // Apply highlights if query is set
    if (props.highlightQuery) {
      applyHighlights(textLayerDiv, props.highlightQuery)
    }
  } catch (err: any) {
    if (err?.name !== 'RenderingCancelledException') {
      console.error('Failed to render page:', err)
      error.value = err?.message || 'Failed to render page'
    }
  } finally {
    rendering = false
    if (pendingRender) {
      pendingRender = false
      await renderPage()
    }
  }
}

function applyHighlights(container: HTMLDivElement, query: string) {
  if (!query.trim()) return

  const lowerQuery = query.toLowerCase()
  const spans = container.querySelectorAll('span')

  for (const span of spans) {
    const text = span.textContent || ''
    const lowerText = text.toLowerCase()
    const idx = lowerText.indexOf(lowerQuery)
    if (idx === -1) continue

    // Build highlighted content
    const frag = document.createDocumentFragment()
    let lastIdx = 0
    let searchIdx = 0

    while (searchIdx < text.length) {
      const pos = lowerText.indexOf(lowerQuery, searchIdx)
      if (pos === -1) break

      // Text before match
      if (pos > lastIdx) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx, pos)))
      }

      // Highlighted match
      const mark = document.createElement('mark')
      mark.textContent = text.slice(pos, pos + query.length)
      frag.appendChild(mark)

      lastIdx = pos + query.length
      searchIdx = lastIdx
    }

    // Remaining text
    if (lastIdx < text.length) {
      frag.appendChild(document.createTextNode(text.slice(lastIdx)))
    }

    span.textContent = ''
    span.appendChild(frag)
  }

  // Scroll to first highlight
  const firstMark = container.querySelector('mark')
  if (firstMark) {
    firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

onMounted(loadPdf)

watch(() => props.fileUrl, loadPdf)
watch(() => props.page, () => { if (pdfDoc) renderPage() })
watch(() => props.zoom, () => { if (pdfDoc) renderPage() })
watch(() => props.highlightQuery, () => { if (pdfDoc) renderPage() })

onBeforeUnmount(() => {
  if (currentTextLayer) {
    currentTextLayer.cancel()
    currentTextLayer = null
  }
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }
})
</script>

<template>
  <div ref="containerRef" class="h-full w-full overflow-auto" style="background-color: var(--color-bg-tertiary);">
    <div v-if="loading" class="flex items-center justify-center h-full">
      <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
    </div>
    <div v-else-if="error" class="flex flex-col items-center justify-center h-full gap-2 p-4">
      <p class="text-sm font-medium" style="color: var(--color-danger);">PDF Error</p>
      <p class="text-xs text-center max-w-[300px]" style="color: var(--color-text-secondary);">{{ error }}</p>
    </div>
    <div v-else class="pdf-page-container relative inline-block mx-auto">
      <canvas ref="canvasRef" />
      <div ref="textLayerRef" class="text-layer absolute top-0 left-0" />
    </div>
  </div>
</template>

<style scoped>
.pdf-page-container {
  display: flex;
  justify-content: center;
}

.text-layer {
  overflow: hidden;
  opacity: 0.25;
  line-height: 1;
}

.text-layer :deep(span) {
  position: absolute;
  white-space: pre;
  color: transparent;
  pointer-events: all;
}

.text-layer :deep(span)::selection {
  background: rgba(0, 100, 200, 0.3);
}

.text-layer :deep(mark) {
  background: var(--color-highlight, rgba(251, 191, 36, 0.4));
  color: transparent;
  border-radius: 2px;
  padding: 1px 0;
}
</style>
