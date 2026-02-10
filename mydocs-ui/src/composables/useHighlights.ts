import { ref, computed } from 'vue'
import type { DocumentElement, HighlightRect } from '@/types'

export function useHighlights(elements: DocumentElement[], pageNumber: number, searchContent?: string) {
  const activeHighlight = ref<HighlightRect | null>(null)

  const highlights = computed<HighlightRect[]>(() => {
    if (!searchContent || !elements.length) return []

    const pageElements = elements.filter(el => el.page_number === pageNumber)
    const rects: HighlightRect[] = []

    for (const el of pageElements) {
      const elContent = el.element_data?.content || ''
      if (!elContent) continue

      // Check if element content overlaps with search content
      const searchLower = searchContent.toLowerCase()
      const elLower = elContent.toLowerCase()
      if (!elLower.includes(searchLower) && !searchLower.includes(elLower.substring(0, 50))) continue

      // Extract bounding regions
      const regions = el.element_data?.boundingRegions || []
      for (const region of regions) {
        if (region.pageNumber !== pageNumber) continue
        const polygon = region.polygon
        if (!polygon || polygon.length < 8) continue

        // Convert polygon to rect (min/max of points)
        const xs = [polygon[0], polygon[2], polygon[4], polygon[6]]
        const ys = [polygon[1], polygon[3], polygon[5], polygon[7]]
        const minX = Math.min(...xs)
        const maxX = Math.max(...xs)
        const minY = Math.min(...ys)
        const maxY = Math.max(...ys)

        rects.push({
          x: minX,
          y: minY,
          width: maxX - minX,
          height: maxY - minY,
          text: elContent.substring(0, 100),
          elementId: el.id,
          elementType: el.type,
        })
      }
    }

    return rects
  })

  function scrollToFirstHighlight() {
    // Will be handled by the viewer component
  }

  return { highlights, activeHighlight, scrollToFirstHighlight }
}
