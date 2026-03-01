<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'

const props = withDefaults(defineProps<{
  direction: 'horizontal' | 'vertical'
  initialRatio?: number
  minRatio?: number
  maxRatio?: number
}>(), {
  initialRatio: 0.6,
  minRatio: 0.2,
  maxRatio: 0.8,
})

const ratio = ref(props.initialRatio)
const isDragging = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const isHorizontal = computed(() => props.direction === 'horizontal')

const firstStyle = computed(() => {
  const pct = ratio.value * 100
  return isHorizontal.value
    ? { height: `${pct}%`, width: '100%' }
    : { width: `${pct}%`, height: '100%' }
})

const secondStyle = computed(() => {
  const pct = (1 - ratio.value) * 100
  return isHorizontal.value
    ? { height: `${pct}%`, width: '100%' }
    : { width: `${pct}%`, height: '100%' }
})

function onDividerMouseDown(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value || !containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  let newRatio: number

  if (isHorizontal.value) {
    newRatio = (e.clientY - rect.top) / rect.height
  } else {
    newRatio = (e.clientX - rect.left) / rect.width
  }

  ratio.value = Math.min(props.maxRatio, Math.max(props.minRatio, newRatio))
}

function onMouseUp() {
  isDragging.value = false
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
})
</script>

<template>
  <div
    ref="containerRef"
    class="flex overflow-hidden"
    :class="isHorizontal ? 'flex-col' : 'flex-row'"
    style="height: 100%; width: 100%;"
  >
    <div class="overflow-hidden" :style="firstStyle">
      <slot name="first" />
    </div>

    <!-- Divider -->
    <div
      :class="[
        'shrink-0 z-10 transition-colors',
        isHorizontal
          ? 'h-1.5 w-full cursor-row-resize hover:bg-[var(--color-accent)]/20'
          : 'w-1.5 h-full cursor-col-resize hover:bg-[var(--color-accent)]/20',
      ]"
      :style="{
        backgroundColor: isDragging ? 'var(--color-accent)' : 'var(--color-border)',
      }"
      @mousedown="onDividerMouseDown"
    />

    <div class="overflow-hidden" :style="secondStyle">
      <slot name="second" />
    </div>
  </div>
</template>
