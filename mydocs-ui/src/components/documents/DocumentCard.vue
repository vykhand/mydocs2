<script setup lang="ts">
import type { Document } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import AddToCaseMenu from '@/components/cases/AddToCaseMenu.vue'
import { getPageThumbnailUrl } from '@/api/documents'
import { formatFileSize, getDisplayStatus } from '@/utils/format'
import { FileText, Files, Layers } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{
  document: Document
}>()

const thumbnailUrl = computed(() => getPageThumbnailUrl(props.document.id, 1))
const displayStatus = computed(() => getDisplayStatus(props.document))
const pageCount = computed(() => props.document.file_metadata?.page_count ?? 0)
const subDocCount = computed(() => props.document.subdocuments?.length ?? 0)
const fileSize = computed(() => formatFileSize(props.document.file_metadata?.size_bytes))

const statusBadgeStyle = computed(() => {
  const colorMap: Record<string, { bg: string; text: string }> = {
    gray: { bg: 'var(--color-bg-tertiary)', text: 'var(--color-text-secondary)' },
    amber: { bg: '#FEF3C7', text: 'var(--color-warning)' },
    green: { bg: '#DCFCE7', text: 'var(--color-success)' },
    blue: { bg: '#DBEAFE', text: '#2563EB' },
    red: { bg: '#FEE2E2', text: 'var(--color-danger)' },
  }
  return colorMap[displayStatus.value.color] || colorMap.gray
})
</script>

<template>
  <div
    class="relative group rounded-lg border cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="$router.push(`/doc/${document.id}`)"
  >
    <!-- Thumbnail -->
    <div class="w-full h-36 overflow-hidden" style="background-color: var(--color-bg-tertiary);">
      <img
        :src="thumbnailUrl"
        :alt="document.original_file_name"
        class="w-full h-full object-cover object-top"
        loading="lazy"
        @error="($event.target as HTMLImageElement).style.display = 'none'"
      />
      <!-- Fallback icon when no thumbnail -->
      <div class="w-full h-full flex items-center justify-center">
        <FileText :size="32" style="color: var(--color-text-secondary); opacity: 0.3;" />
      </div>
    </div>

    <!-- Status badge overlay -->
    <span
      class="absolute top-2 left-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
      :style="{ backgroundColor: statusBadgeStyle.bg, color: statusBadgeStyle.text }"
    >
      {{ displayStatus.label }}
    </span>

    <!-- Content -->
    <div class="p-3">
      <p class="text-sm font-medium truncate" style="color: var(--color-text-primary);">
        {{ document.original_file_name }}
      </p>
      <div class="flex items-center gap-3 mt-1.5 text-xs" style="color: var(--color-text-secondary);">
        <FileTypeBadge :file-type="document.file_type" />
        <span v-if="pageCount" class="flex items-center gap-1">
          <Files :size="12" /> {{ pageCount }}
        </span>
        <span v-if="subDocCount" class="flex items-center gap-1">
          <Layers :size="12" /> {{ subDocCount }}
        </span>
        <span>{{ fileSize }}</span>
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
    <div
      class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
      @click.stop
    >
      <AddToCaseMenu :document-ids="[document.id]" />
    </div>
  </div>
</template>
