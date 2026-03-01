<script setup lang="ts">
import { ref } from 'vue'
import type { ElementAnnotation } from '@/types'
import { ELEMENT_TYPE_COLORS, ELEMENT_TYPE_BORDER_COLORS, ELEMENT_TYPE_LABELS } from '@/types'

defineProps<{
  annotations: ElementAnnotation[]
  activeElementId: string | null
}>()

const emit = defineEmits<{
  select: [elementId: string]
}>()

const tooltip = ref<{ visible: boolean; x: number; y: number; annotation: ElementAnnotation | null }>({
  visible: false,
  x: 0,
  y: 0,
  annotation: null,
})

function onMouseEnter(e: MouseEvent, ann: ElementAnnotation) {
  tooltip.value = {
    visible: true,
    x: e.clientX + 12,
    y: e.clientY + 12,
    annotation: ann,
  }
}

function onMouseMove(e: MouseEvent) {
  if (tooltip.value.visible) {
    tooltip.value.x = e.clientX + 12
    tooltip.value.y = e.clientY + 12
  }
}

function onMouseLeave() {
  tooltip.value = { visible: false, x: 0, y: 0, annotation: null }
}
</script>

<template>
  <div class="absolute inset-0 pointer-events-none">
    <div
      v-for="ann in annotations"
      :key="ann.elementId"
      class="absolute pointer-events-auto cursor-pointer transition-opacity duration-150"
      :style="{
        left: ann.x + '%',
        top: ann.y + '%',
        width: ann.width + '%',
        height: ann.height + '%',
        backgroundColor: ELEMENT_TYPE_COLORS[ann.type],
        border: '1px solid ' + ELEMENT_TYPE_BORDER_COLORS[ann.type],
        opacity: activeElementId && activeElementId !== ann.elementId ? 0.3 : 1,
        boxShadow: activeElementId === ann.elementId
          ? '0 0 0 2px ' + ELEMENT_TYPE_BORDER_COLORS[ann.type] + ', 0 0 8px ' + ELEMENT_TYPE_COLORS[ann.type]
          : 'none',
      }"
      @click.stop="emit('select', ann.elementId)"
      @mouseenter="onMouseEnter($event, ann)"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
    />

    <!-- Tooltip -->
    <Teleport to="body">
      <div
        v-if="tooltip.visible && tooltip.annotation"
        class="fixed z-[100] px-3 py-2 rounded shadow-lg text-xs max-w-xs pointer-events-none"
        :style="{
          left: tooltip.x + 'px',
          top: tooltip.y + 'px',
          backgroundColor: 'var(--color-bg-secondary)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-text-primary)',
        }"
      >
        <div class="font-semibold flex items-center gap-1.5 mb-1">
          <span
            class="inline-block w-2.5 h-2.5 rounded-full shrink-0"
            :style="{ backgroundColor: ELEMENT_TYPE_BORDER_COLORS[tooltip.annotation.type] }"
          />
          {{ ELEMENT_TYPE_LABELS[tooltip.annotation.type] }}
          <span v-if="tooltip.annotation.shortId" class="font-mono text-[10px] opacity-60">
            {{ tooltip.annotation.shortId }}
          </span>
        </div>
        <div class="truncate" style="color: var(--color-text-secondary);">
          {{ tooltip.annotation.contentPreview }}
        </div>
      </div>
    </Teleport>
  </div>
</template>
