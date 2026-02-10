<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps<{
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const startItem = computed(() => Math.min((props.page - 1) * props.pageSize + 1, props.total))
const endItem = computed(() => Math.min(props.page * props.pageSize, props.total))
</script>

<template>
  <div class="flex items-center justify-between gap-4 text-sm" style="color: var(--color-text-secondary);">
    <div class="flex items-center gap-2">
      <span>Rows:</span>
      <select
        :value="pageSize"
        @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value)); emit('update:page', 1)"
        class="rounded border px-2 py-1 text-sm"
        style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
      >
        <option :value="25">25</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
    </div>
    <span>{{ startItem }}-{{ endItem }} of {{ total }}</span>
    <div class="flex items-center gap-1">
      <button
        @click="emit('update:page', page - 1)"
        :disabled="page <= 1"
        class="p-1 rounded disabled:opacity-30 transition-opacity"
        style="color: var(--color-text-secondary);"
      >
        <ChevronLeft :size="18" />
      </button>
      <span class="px-2">{{ page }} / {{ totalPages }}</span>
      <button
        @click="emit('update:page', page + 1)"
        :disabled="page >= totalPages"
        class="p-1 rounded disabled:opacity-30 transition-opacity"
        style="color: var(--color-text-secondary);"
      >
        <ChevronRight :size="18" />
      </button>
    </div>
  </div>
</template>
