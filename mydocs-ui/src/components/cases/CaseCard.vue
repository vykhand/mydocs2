<script setup lang="ts">
import type { Case } from '@/types'
import { Briefcase } from 'lucide-vue-next'

defineProps<{
  caseData: Case
}>()

defineEmits<{
  click: []
}>()

function formatDate(d?: string) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}
</script>

<template>
  <div
    class="rounded-lg border p-4 cursor-pointer hover:shadow-md transition-shadow"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style="background-color: var(--color-bg-tertiary);"
      >
        <Briefcase :size="20" style="color: var(--color-text-secondary);" />
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate" style="color: var(--color-text-primary);">
          {{ caseData.name }}
        </p>
        <p v-if="caseData.description" class="text-xs mt-0.5 truncate" style="color: var(--color-text-secondary);">
          {{ caseData.description }}
        </p>
        <div class="flex items-center gap-3 mt-2 text-xs" style="color: var(--color-text-secondary);">
          <span>{{ caseData.document_ids?.length || 0 }} docs</span>
          <span>{{ formatDate(caseData.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
