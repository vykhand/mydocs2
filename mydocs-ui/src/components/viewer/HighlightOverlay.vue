<script setup lang="ts">
import type { HighlightRect } from '@/types'

defineProps<{
  highlights: HighlightRect[]
  zoom: number
  pageWidth: number
  pageHeight: number
}>()

const emit = defineEmits<{
  select: [highlight: HighlightRect]
}>()
</script>

<template>
  <div class="absolute inset-0 pointer-events-none">
    <div
      v-for="(h, i) in highlights"
      :key="i"
      class="absolute pointer-events-auto cursor-pointer transition-opacity"
      :style="{
        left: (h.x / pageWidth * 100) + '%',
        top: (h.y / pageHeight * 100) + '%',
        width: (h.width / pageWidth * 100) + '%',
        height: (h.height / pageHeight * 100) + '%',
        backgroundColor: 'var(--color-highlight)',
        opacity: 0.4,
        borderRadius: '2px',
      }"
      :title="h.text"
      @click="emit('select', h)"
    />
  </div>
</template>
