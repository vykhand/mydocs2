<script setup lang="ts">
defineProps<{
  totalPages: number
  currentPage: number
}>()

const emit = defineEmits<{
  goToPage: [page: number]
}>()
</script>

<template>
  <div
    class="w-20 shrink-0 border-r overflow-y-auto p-2 space-y-2"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
  >
    <button
      v-for="p in totalPages"
      :key="p"
      @click="emit('goToPage', p)"
      class="w-full aspect-[3/4] rounded border text-xs font-medium flex items-center justify-center transition-all"
      :style="{
        borderColor: p === currentPage ? 'var(--color-accent)' : 'var(--color-border)',
        backgroundColor: p === currentPage ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
        color: p === currentPage ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        boxShadow: p === currentPage ? '0 0 0 2px var(--color-accent)' : 'none',
      }"
    >
      {{ p }}
    </button>
  </div>
</template>
