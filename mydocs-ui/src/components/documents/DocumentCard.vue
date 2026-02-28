<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Document } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import AddToCaseMenu from '@/components/cases/AddToCaseMenu.vue'
import { getDocumentThumbnailUrl } from '@/api/documents'
import { FileText, Files, HardDrive } from 'lucide-vue-next'

const props = defineProps<{
  document: Document
}>()

const thumbError = ref(false)
const thumbLoaded = ref(false)

const thumbnailUrl = computed(() => getDocumentThumbnailUrl(props.document.id, 300))

const pageCount = computed(() => props.document.file_metadata?.page_count || 0)

const sizeDisplay = computed(() => {
  const bytes = props.document.file_metadata?.size_bytes
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

function onThumbLoad() {
  thumbLoaded.value = true
  thumbError.value = false
}

function onThumbError() {
  thumbError.value = true
  thumbLoaded.value = false
}
</script>

<template>
  <div
    class="relative group rounded-lg border overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
    style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    @click="$router.push(`/doc/${document.id}`)"
  >
    <!-- Thumbnail area -->
    <div
      class="w-full aspect-[4/3] flex items-center justify-center overflow-hidden"
      style="background-color: var(--color-bg-tertiary);"
    >
      <img
        v-if="!thumbError"
        :src="thumbnailUrl"
        class="w-full h-full object-cover"
        :class="{ 'opacity-0': !thumbLoaded }"
        loading="lazy"
        @load="onThumbLoad"
        @error="onThumbError"
      />
      <FileText v-if="thumbError || !thumbLoaded" :size="36" style="color: var(--color-text-secondary);" :class="{ 'absolute': !thumbError && !thumbLoaded }" />
    </div>

    <!-- Info area -->
    <div class="p-3">
      <p class="text-sm font-medium truncate" style="color: var(--color-text-primary);">
        {{ document.original_file_name }}
      </p>
      <div class="flex items-center gap-2 mt-1.5">
        <FileTypeBadge :file-type="document.file_type" />
        <StatusBadge :status="document.status" />
      </div>
      <!-- Metadata row: pages, size -->
      <div class="flex items-center gap-3 mt-2 text-xs" style="color: var(--color-text-secondary);">
        <span v-if="pageCount" class="flex items-center gap-1">
          <Files :size="12" />
          {{ pageCount }} {{ pageCount === 1 ? 'page' : 'pages' }}
        </span>
        <span v-if="sizeDisplay" class="flex items-center gap-1">
          <HardDrive :size="12" />
          {{ sizeDisplay }}
        </span>
      </div>
      <!-- Tags -->
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

    <!-- Hover overlay -->
    <div
      class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
      @click.stop
    >
      <AddToCaseMenu :document-ids="[document.id]" />
    </div>
  </div>
</template>
