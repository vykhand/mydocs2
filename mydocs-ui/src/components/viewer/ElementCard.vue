<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { DocumentElement } from '@/types'
import { ELEMENT_TYPE_BORDER_COLORS } from '@/types'

const props = defineProps<{
  element: DocumentElement
  isActive: boolean
}>()

defineEmits<{
  select: [elementId: string]
}>()

const cardRef = ref<HTMLElement | null>(null)

watch(() => props.isActive, async (active) => {
  if (active && cardRef.value) {
    await nextTick()
    cardRef.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
})

function getContentPreview(el: DocumentElement): string {
  if (el.type === 'key_value_pair') {
    const key = el.element_data?.key?.content || ''
    const value = el.element_data?.value?.content || ''
    return `${key}: ${value}`
  }
  if (el.type === 'table') {
    const rows = el.element_data?.rowCount || '?'
    const cols = el.element_data?.columnCount || '?'
    return `Table: ${rows}x${cols}`
  }
  return el.element_data?.content || ''
}
</script>

<template>
  <div
    ref="cardRef"
    class="px-3 py-2 rounded cursor-pointer transition-all duration-150 border"
    :style="{
      backgroundColor: isActive ? 'var(--color-bg-tertiary)' : 'transparent',
      borderColor: isActive ? ELEMENT_TYPE_BORDER_COLORS[element.type] : 'transparent',
      boxShadow: isActive ? '0 0 0 1px ' + ELEMENT_TYPE_BORDER_COLORS[element.type] : 'none',
    }"
    @click="$emit('select', element.id)"
  >
    <div class="flex items-center gap-2 mb-1">
      <span
        v-if="element.short_id"
        class="font-mono text-[10px] px-1.5 py-0.5 rounded"
        style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
      >
        {{ element.short_id }}
      </span>
      <span
        class="text-[10px] px-1.5 py-0.5 rounded"
        style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
      >
        p.{{ element.page_number }}
      </span>
    </div>
    <p
      class="text-xs line-clamp-2"
      style="color: var(--color-text-secondary);"
    >
      {{ getContentPreview(element) }}
    </p>

    <!-- Expanded content when active -->
    <div
      v-if="isActive && getContentPreview(element).length > 80"
      class="mt-2 pt-2 border-t text-xs"
      style="border-color: var(--color-border); color: var(--color-text-secondary);"
    >
      {{ getContentPreview(element) }}
    </div>
  </div>
</template>
