<script setup lang="ts">
defineProps<{
  scores: Record<string, number>
  total: number
}>()
</script>

<template>
  <div class="space-y-1.5">
    <div v-for="(score, key) in scores" :key="key" class="flex items-center gap-2">
      <span class="text-xs w-16 text-right capitalize" style="color: var(--color-text-secondary);">{{ key }}</span>
      <div class="flex-1 h-1.5 rounded-full" style="background-color: var(--color-bg-tertiary);">
        <div
          class="h-full rounded-full"
          :style="{
            width: Math.round(score * 100) + '%',
            backgroundColor: key === 'fulltext' ? 'var(--color-warning)' : key === 'vector' ? 'var(--color-success)' : 'var(--color-accent)',
          }"
        />
      </div>
      <span class="text-xs w-10 font-mono" style="color: var(--color-text-secondary);">{{ score.toFixed(3) }}</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-xs w-16 text-right font-medium" style="color: var(--color-text-primary);">Combined</span>
      <div class="flex-1 h-1.5 rounded-full" style="background-color: var(--color-bg-tertiary);">
        <div
          class="h-full rounded-full"
          style="background-color: var(--color-accent);"
          :style="{ width: Math.round(total * 100) + '%' }"
        />
      </div>
      <span class="text-xs w-10 font-mono font-medium" style="color: var(--color-text-primary);">{{ total.toFixed(3) }}</span>
    </div>
  </div>
</template>
