<script setup lang="ts">
import { computed } from 'vue'
import type { DocumentStatus } from '@/types'

const props = defineProps<{
  status: DocumentStatus
}>()

const config = computed(() => {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    new: { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)', label: 'New' },
    parsing: { bg: '#FEF3C7', text: 'var(--color-warning)', label: 'Parsing' },
    parsed: { bg: '#DCFCE7', text: 'var(--color-success)', label: 'Parsed' },
    failed: { bg: '#FEE2E2', text: 'var(--color-danger)', label: 'Failed' },
    skipped: { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)', label: 'Skipped' },
    not_supported: { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)', label: 'Not Supported' },
  }
  return map[props.status] || map.new
})
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
    :style="{ backgroundColor: config.bg, color: config.text }"
  >
    {{ config.label }}
  </span>
</template>
