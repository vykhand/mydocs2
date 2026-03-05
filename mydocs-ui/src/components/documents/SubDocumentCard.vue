<script setup lang="ts">
import type { SubDocument } from '@/types'
import { fetchPageThumbnailBlob } from '@/api/documents'
import { FileText } from 'lucide-vue-next'
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps<{
  subdocument: SubDocument
  parentDocumentId: string
}>()

const emit = defineEmits<{
  click: [subdoc: SubDocument]
}>()

const thumbnailUrl = ref('')

const firstPage = computed(() => {
  if (!props.subdocument.page_refs?.length) return null
  return props.subdocument.page_refs.reduce(
    (min, ref) => ref.page_number < min.page_number ? ref : min,
    props.subdocument.page_refs[0],
  )
})

const pageRange = computed(() => {
  const refs = props.subdocument.page_refs || []
  if (!refs.length) return ''
  const pages = refs.map(r => r.page_number).sort((a, b) => a - b)
  if (pages.length === 1) return `Page ${pages[0]}`
  return `Pages ${pages[0]}–${pages[pages.length - 1]}`
})

const formattedDate = computed(() => {
  if (!props.subdocument.created_at) return ''
  return new Date(props.subdocument.created_at).toLocaleDateString()
})

onMounted(async () => {
  if (firstPage.value) {
    try {
      thumbnailUrl.value = await fetchPageThumbnailBlob(
        props.parentDocumentId,
        firstPage.value.page_number,
        600,
      )
    } catch {
      // Thumbnail not available
    }
  }
})

onBeforeUnmount(() => {
  if (thumbnailUrl.value) URL.revokeObjectURL(thumbnailUrl.value)
})
</script>

<template>
  <div
    class="relative group rounded-lg border-2 cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
    :style="{
      borderColor: 'var(--color-border)',
      backgroundColor: 'var(--color-bg-secondary)',
    }"
    @click="emit('click', subdocument)"
  >
    <!-- Thumbnail -->
    <div class="w-full h-48 overflow-hidden" style="background-color: var(--color-bg-tertiary);">
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        :alt="subdocument.document_type"
        class="w-full h-full object-contain object-top"
      />
      <div v-else class="w-full h-full flex items-center justify-center">
        <FileText :size="32" style="color: var(--color-text-secondary); opacity: 0.3;" />
      </div>
    </div>

    <!-- Document type badge overlay -->
    <span
      class="absolute top-2 left-2 inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold"
      style="background-color: #DBEAFE; color: #2563EB;"
    >
      {{ subdocument.document_type }}
    </span>

    <!-- Content -->
    <div class="p-3">
      <p class="text-sm font-medium" style="color: var(--color-text-primary);">
        {{ subdocument.document_type }}
      </p>
      <div class="flex items-center gap-3 mt-1.5 text-xs" style="color: var(--color-text-secondary);">
        <span>{{ pageRange }}</span>
        <span v-if="formattedDate">{{ formattedDate }}</span>
      </div>
    </div>
  </div>
</template>
