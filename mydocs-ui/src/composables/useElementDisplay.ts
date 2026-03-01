import { computed, type Ref } from 'vue'
import type { DocumentElement, DocumentPage, ElementAnnotation } from '@/types'

export function useElementDisplay(
  elements: Ref<DocumentElement[] | undefined>,
  pages: Ref<DocumentPage[]>,
  currentPage: Ref<number>,
) {
  const pageElements = computed<DocumentElement[]>(() => {
    if (!elements.value) return []
    return elements.value.filter(el => el.page_number === currentPage.value)
  })

  const currentPageDimensions = computed(() => {
    const page = pages.value.find(p => p.page_number === currentPage.value)
    if (!page || !page.width || !page.height) return null
    return { width: page.width, height: page.height, unit: page.unit || 'inch' }
  })

  const pageElementsByType = computed<Record<string, DocumentElement[]>>(() => {
    const grouped: Record<string, DocumentElement[]> = {}
    for (const el of pageElements.value) {
      if (!grouped[el.type]) grouped[el.type] = []
      grouped[el.type].push(el)
    }
    return grouped
  })

  function getContentPreview(el: DocumentElement): string {
    if (el.type === 'key_value_pair') {
      const key = el.element_data?.key?.content || ''
      const value = el.element_data?.value?.content || ''
      return `${key}: ${value}`.substring(0, 120)
    }
    if (el.type === 'table') {
      const rows = el.element_data?.rowCount || '?'
      const cols = el.element_data?.columnCount || '?'
      return `Table: ${rows}x${cols}`
    }
    const content = el.element_data?.content || ''
    return content.substring(0, 120)
  }

  function extractRegions(el: DocumentElement): Array<{ polygon: number[]; pageNumber: number }> {
    const regions: Array<{ polygon: number[]; pageNumber: number }> = []

    if (el.type === 'key_value_pair') {
      // Union key and value bounding regions
      const keyRegions = el.element_data?.key?.boundingRegions || []
      const valueRegions = el.element_data?.value?.boundingRegions || []
      for (const r of [...keyRegions, ...valueRegions]) {
        if (r.polygon && r.polygon.length >= 8) {
          regions.push({ polygon: r.polygon, pageNumber: r.pageNumber })
        }
      }
    } else {
      const boundingRegions = el.element_data?.boundingRegions || []
      for (const r of boundingRegions) {
        if (r.polygon && r.polygon.length >= 8) {
          regions.push({ polygon: r.polygon, pageNumber: r.pageNumber })
        }
      }
    }

    return regions
  }

  const annotations = computed<ElementAnnotation[]>(() => {
    const dims = currentPageDimensions.value
    if (!dims) return []

    const result: ElementAnnotation[] = []

    for (const el of pageElements.value) {
      const regions = extractRegions(el)
      const pageRegions = regions.filter(r => r.pageNumber === currentPage.value)

      if (pageRegions.length === 0) continue

      // Compute bounding box across all regions for this element on this page
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity

      for (const region of pageRegions) {
        const polygon = region.polygon
        const xs = [polygon[0], polygon[2], polygon[4], polygon[6]]
        const ys = [polygon[1], polygon[3], polygon[5], polygon[7]]
        minX = Math.min(minX, ...xs)
        maxX = Math.max(maxX, ...xs)
        minY = Math.min(minY, ...ys)
        maxY = Math.max(maxY, ...ys)
      }

      result.push({
        elementId: el.id,
        shortId: el.short_id,
        type: el.type,
        x: (minX / dims.width) * 100,
        y: (minY / dims.height) * 100,
        width: ((maxX - minX) / dims.width) * 100,
        height: ((maxY - minY) / dims.height) * 100,
        contentPreview: getContentPreview(el),
        pageNumber: el.page_number,
      })
    }

    return result
  })

  return {
    pageElements,
    currentPageDimensions,
    annotations,
    pageElementsByType,
  }
}
