import type { Document } from '@/types'

export function formatFileSize(bytes?: number): string {
  if (bytes == null || bytes === 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

export function getDisplayStatus(doc: Document): { label: string; color: string } {
  if (doc.status === 'parsed' && doc.subdocuments?.length) {
    return { label: 'Classified', color: 'blue' }
  }
  const map: Record<string, { label: string; color: string }> = {
    new: { label: 'New', color: 'gray' },
    parsing: { label: 'Parsing', color: 'amber' },
    parsed: { label: 'Parsed', color: 'green' },
    failed: { label: 'Failed', color: 'red' },
    skipped: { label: 'Skipped', color: 'gray' },
    not_supported: { label: 'Not Supported', color: 'gray' },
  }
  return map[doc.status] || map.new
}
