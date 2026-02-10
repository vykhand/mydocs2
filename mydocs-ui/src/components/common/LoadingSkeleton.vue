<script setup lang="ts">
withDefaults(defineProps<{
  lines?: number
  showAvatar?: boolean
}>(), {
  lines: 3,
  showAvatar: false,
})
</script>

<template>
  <div class="animate-pulse space-y-3">
    <div v-if="showAvatar" class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-full" style="background-color: var(--color-bg-tertiary);" />
      <div class="flex-1 space-y-2">
        <div class="h-4 rounded w-1/3" style="background-color: var(--color-bg-tertiary);" />
        <div class="h-3 rounded w-1/2" style="background-color: var(--color-bg-tertiary);" />
      </div>
    </div>
    <div
      v-for="i in lines"
      :key="i"
      class="h-4 rounded"
      :style="{
        backgroundColor: 'var(--color-bg-tertiary)',
        width: i === lines ? '60%' : '100%',
      }"
    />
  </div>
</template>
