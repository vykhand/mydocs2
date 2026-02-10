<script setup lang="ts">
import { computed } from 'vue'
import type { FileType } from '@/types'

const props = defineProps<{
  fileType: FileType
}>()

const label = computed(() => props.fileType.toUpperCase())
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium"
    style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
  >
    {{ label }}
  </span>
</template>
