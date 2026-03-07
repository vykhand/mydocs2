<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import { ArrowLeft, ChevronDown, ChevronRight } from 'lucide-vue-next'
import SubDocumentCard from './SubDocumentCard.vue'
import type { Document, SubDocument } from '@/types'

const props = defineProps<{
  parentDocument: Document
}>()

const emit = defineEmits<{
  back: []
  openSubdoc: [subdoc: SubDocument]
}>()

const appStore = useAppStore()

const subdocuments = computed(() => props.parentDocument.subdocuments || [])

// Group subdocuments by document_type for list view
const groupedByType = computed(() => {
  const groups: Record<string, SubDocument[]> = {}
  for (const subdoc of subdocuments.value) {
    const type = subdoc.document_type || 'Unknown'
    if (!groups[type]) groups[type] = []
    groups[type].push(subdoc)
  }
  return groups
})

const groupTypes = computed(() => Object.keys(groupedByType.value).sort())

// Track collapsed groups
const collapsedGroups = ref<Set<string>>(new Set())

function toggleGroup(type: string) {
  if (collapsedGroups.value.has(type)) {
    collapsedGroups.value.delete(type)
  } else {
    collapsedGroups.value.add(type)
  }
}

function getPageRange(subdoc: SubDocument): string {
  const refs = subdoc.page_refs || []
  if (!refs.length) return ''
  const pages = refs.map(r => r.page_number).sort((a, b) => a - b)
  if (pages.length === 1) return `Page ${pages[0]}`
  return `Pages ${pages[0]}–${pages[pages.length - 1]}`
}

function formatDate(d?: string): string {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}
</script>

<template>
  <div>
    <!-- Breadcrumb header -->
    <div class="flex items-center gap-2 mb-4">
      <button
        class="p-1.5 rounded-lg hover:opacity-70 transition-opacity"
        style="color: var(--color-text-secondary);"
        :title="appStore.subdocViewFromSearch ? 'Back to search results' : 'Back to documents'"
        @click="emit('back')"
      >
        <ArrowLeft :size="20" />
      </button>
      <nav class="flex items-center gap-1 text-sm">
        <button
          class="hover:underline"
          style="color: var(--color-accent);"
          @click="emit('back')"
        >
          {{ appStore.subdocViewFromSearch ? 'Search Results' : 'Documents' }}
        </button>
        <span style="color: var(--color-text-secondary);">/</span>
        <span class="font-medium" style="color: var(--color-text-primary);">
          {{ parentDocument.original_file_name }}
        </span>
      </nav>
    </div>

    <!-- Sub-document count -->
    <p class="text-sm mb-4" style="color: var(--color-text-secondary);">
      {{ subdocuments.length }} sub-document{{ subdocuments.length !== 1 ? 's' : '' }}
    </p>

    <!-- Grid mode -->
    <div v-if="appStore.galleryViewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <SubDocumentCard
        v-for="subdoc in subdocuments"
        :key="subdoc.id"
        :subdocument="subdoc"
        :parent-document-id="parentDocument.id"
        @click="emit('openSubdoc', subdoc)"
      />
    </div>

    <!-- List mode: grouped by type -->
    <div v-else class="space-y-2">
      <div
        v-for="type in groupTypes"
        :key="type"
        class="rounded-lg border overflow-hidden"
        style="border-color: var(--color-border);"
      >
        <!-- Group header -->
        <button
          class="w-full flex items-center gap-2 px-4 py-3 text-left font-medium text-sm transition-colors"
          style="background-color: var(--color-bg-secondary); color: var(--color-text-primary);"
          @click="toggleGroup(type)"
        >
          <component
            :is="collapsedGroups.has(type) ? ChevronRight : ChevronDown"
            :size="16"
            style="color: var(--color-text-secondary);"
          />
          <span
            class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
            style="background-color: #DBEAFE; color: #2563EB;"
          >
            {{ type }}
          </span>
          <span class="text-xs" style="color: var(--color-text-secondary);">
            ({{ groupedByType[type].length }})
          </span>
        </button>

        <!-- Group items -->
        <div v-if="!collapsedGroups.has(type)">
          <div
            v-for="subdoc in groupedByType[type]"
            :key="subdoc.id"
            class="flex items-center gap-4 px-4 py-3 border-t cursor-pointer hover:opacity-90 transition-opacity"
            style="border-color: var(--color-border);"
            @click="emit('openSubdoc', subdoc)"
          >
            <span
              class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0"
              style="background-color: #DBEAFE; color: #2563EB;"
            >
              {{ subdoc.document_type }}
            </span>
            <span class="text-sm" style="color: var(--color-text-secondary);">
              {{ getPageRange(subdoc) }}
            </span>
            <span class="text-xs ml-auto" style="color: var(--color-text-secondary);">
              {{ formatDate(subdoc.created_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
