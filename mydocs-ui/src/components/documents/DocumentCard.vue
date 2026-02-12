<script setup lang="ts">
import type { Document } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import { FileText } from 'lucide-vue-next'

defineProps<{
  document: Document
}>()
</script>

<template>
  <div
    class="rounded-lg border p-4 cursor-pointer hover:shadow-md transition-shadow"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="$router.push(`/doc/${document.id}`)"
  >
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style="background-color: var(--color-bg-tertiary);"
      >
        <FileText :size="20" style="color: var(--color-text-secondary);" />
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate" style="color: var(--color-text-primary);">
          {{ document.original_file_name }}
        </p>
        <div class="flex items-center gap-2 mt-1">
          <FileTypeBadge :file-type="document.file_type" />
          <StatusBadge :status="document.status" />
        </div>
        <div class="flex flex-wrap gap-1 mt-2" v-if="document.tags?.length">
          <span
            v-for="tag in document.tags.slice(0, 3)"
            :key="tag"
            class="px-1.5 py-0.5 rounded text-xs"
            style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
