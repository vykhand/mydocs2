<script setup lang="ts">
const props = defineProps<{
  startDate?: string
  endDate?: string
}>()

const emit = defineEmits<{
  'update:startDate': [date: string]
  'update:endDate': [date: string]
}>()
</script>

<template>
  <div class="flex items-center gap-2">
    <input
      type="date"
      :value="startDate"
      @input="emit('update:startDate', ($event.target as HTMLInputElement).value)"
      class="rounded border px-2 py-1.5 text-sm"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      placeholder="Start"
    />
    <span class="text-xs" style="color: var(--color-text-secondary);">to</span>
    <input
      type="date"
      :value="endDate"
      @input="emit('update:endDate', ($event.target as HTMLInputElement).value)"
      class="rounded border px-2 py-1.5 text-sm"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      placeholder="End"
    />
  </div>
</template>
