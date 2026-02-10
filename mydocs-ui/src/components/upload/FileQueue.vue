<script setup lang="ts">
import { X } from 'lucide-vue-next'

defineProps<{
  files: File[]
}>()

const emit = defineEmits<{
  remove: [index: number]
}>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div
    class="rounded-lg border overflow-hidden"
    style="border-color: var(--color-border);"
  >
    <table class="w-full text-sm">
      <thead>
        <tr style="background-color: var(--color-bg-secondary);">
          <th class="text-left px-4 py-2 font-medium" style="color: var(--color-text-secondary);">Name</th>
          <th class="text-left px-4 py-2 font-medium" style="color: var(--color-text-secondary);">Size</th>
          <th class="text-left px-4 py-2 font-medium" style="color: var(--color-text-secondary);">Type</th>
          <th class="w-10" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(file, i) in files"
          :key="i"
          class="border-t"
          style="border-color: var(--color-border);"
        >
          <td class="px-4 py-2" style="color: var(--color-text-primary);">{{ file.name }}</td>
          <td class="px-4 py-2" style="color: var(--color-text-secondary);">{{ formatSize(file.size) }}</td>
          <td class="px-4 py-2 font-mono text-xs" style="color: var(--color-text-secondary);">{{ file.type || 'unknown' }}</td>
          <td class="px-2 py-2">
            <button @click="emit('remove', i)" class="p-1 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
              <X :size="16" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
