<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useResponsive } from '@/composables/useResponsive'
import { useDocumentViewer } from '@/composables/useDocumentViewer'
import { X, Maximize2, ChevronDown } from 'lucide-vue-next'
import { ref } from 'vue'

const appStore = useAppStore()
const route = useRoute()
const { isMobile, isTablet } = useResponsive()

const showDuplicates = ref(false)
const showMetadata = ref(false)
const showTags = ref(true)
const showAdvanced = ref(false)

const documentId = computed(() => appStore.viewerDocumentId)

const viewer = computed(() => {
  if (!documentId.value) return null
  return useDocumentViewer(documentId.value, appStore.viewerPage)
})

// Watch route query for page changes
watch(() => route.query.page, (p) => {
  if (p && viewer.value) {
    viewer.value.goToPage(Number(p))
  }
})
</script>

<template>
  <aside
    class="flex flex-col overflow-hidden"
    :style="{
      backgroundColor: 'var(--color-bg-secondary)',
      borderColor: 'var(--color-border)',
    }"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b shrink-0" style="border-color: var(--color-border);">
      <h3 class="text-sm font-semibold truncate" style="color: var(--color-text-primary);">
        {{ viewer?.document.value?.original_file_name || 'Document Viewer' }}
      </h3>
      <div class="flex items-center gap-1">
        <button
          class="p-1 rounded hover:opacity-70"
          style="color: var(--color-text-secondary);"
          title="Maximize"
        >
          <Maximize2 :size="16" />
        </button>
        <button
          @click="appStore.closeViewer()"
          class="p-1 rounded hover:opacity-70"
          style="color: var(--color-text-secondary);"
          title="Close"
        >
          <X :size="16" />
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      <!-- PDF/Image viewer placeholder -->
      <div v-if="viewer?.loading.value" class="flex items-center justify-center h-48">
        <div class="animate-spin w-6 h-6 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
      </div>
      <div v-else class="p-4">
        <!-- Document info -->
        <div class="mb-4">
          <p class="text-sm" style="color: var(--color-text-secondary);">
            {{ viewer?.totalPages.value || 0 }} pages
          </p>
          <!-- Page navigation -->
          <div class="flex items-center gap-2 mt-2">
            <button
              @click="viewer?.prevPage()"
              :disabled="viewer?.currentPage.value === 1"
              class="px-2 py-1 text-xs rounded border disabled:opacity-40"
              style="border-color: var(--color-border); color: var(--color-text-primary);"
            >
              Prev
            </button>
            <span class="text-xs" style="color: var(--color-text-secondary);">
              Page {{ viewer?.currentPage.value }} / {{ viewer?.totalPages.value }}
            </span>
            <button
              @click="viewer?.nextPage()"
              :disabled="viewer?.currentPage.value === viewer?.totalPages.value"
              class="px-2 py-1 text-xs rounded border disabled:opacity-40"
              style="border-color: var(--color-border); color: var(--color-text-primary);"
            >
              Next
            </button>
          </div>
        </div>

        <!-- Collapsible sections -->

        <!-- Metadata -->
        <div class="border-t py-3" style="border-color: var(--color-border);">
          <button
            @click="showMetadata = !showMetadata"
            class="flex items-center justify-between w-full text-sm font-medium"
            style="color: var(--color-text-primary);"
          >
            Metadata
            <ChevronDown :size="14" :class="{ 'rotate-180': showMetadata }" class="transition-transform" />
          </button>
          <div v-if="showMetadata" class="mt-2 space-y-1 text-xs" style="color: var(--color-text-secondary);">
            <p v-if="viewer?.document.value?.file_type">Type: {{ viewer.document.value.file_type }}</p>
            <p v-if="viewer?.document.value?.status">Status: {{ viewer.document.value.status }}</p>
            <p v-if="viewer?.document.value?.file_metadata?.size_bytes">Size: {{ Math.round((viewer.document.value.file_metadata.size_bytes || 0) / 1024) }}KB</p>
            <p v-if="viewer?.document.value?.file_metadata?.author">Author: {{ viewer.document.value.file_metadata.author }}</p>
            <p v-if="viewer?.document.value?.created_at">Created: {{ new Date(viewer.document.value.created_at).toLocaleDateString() }}</p>
          </div>
        </div>

        <!-- Tags -->
        <div class="border-t py-3" style="border-color: var(--color-border);">
          <button
            @click="showTags = !showTags"
            class="flex items-center justify-between w-full text-sm font-medium"
            style="color: var(--color-text-primary);"
          >
            Tags
            <ChevronDown :size="14" :class="{ 'rotate-180': showTags }" class="transition-transform" />
          </button>
          <div v-if="showTags" class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="tag in viewer?.document.value?.tags"
              :key="tag"
              class="px-2 py-0.5 rounded text-xs"
              style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
            >
              {{ tag }}
            </span>
            <span v-if="!viewer?.document.value?.tags?.length" class="text-xs" style="color: var(--color-text-secondary);">
              No tags
            </span>
          </div>
        </div>

        <!-- Duplicates -->
        <div class="border-t py-3" style="border-color: var(--color-border);">
          <button
            @click="showDuplicates = !showDuplicates"
            class="flex items-center justify-between w-full text-sm font-medium"
            style="color: var(--color-text-primary);"
          >
            Duplicates
            <ChevronDown :size="14" :class="{ 'rotate-180': showDuplicates }" class="transition-transform" />
          </button>
          <div v-if="showDuplicates" class="mt-2">
            <p class="text-xs" style="color: var(--color-text-secondary);">No duplicates detected.</p>
          </div>
        </div>

        <!-- Advanced -->
        <div class="border-t py-3" style="border-color: var(--color-border);">
          <button
            @click="showAdvanced = !showAdvanced"
            class="flex items-center justify-between w-full text-sm font-medium"
            style="color: var(--color-text-primary);"
          >
            Advanced
            <ChevronDown :size="14" :class="{ 'rotate-180': showAdvanced }" class="transition-transform" />
          </button>
          <div v-if="showAdvanced" class="mt-2 text-xs space-y-1" style="color: var(--color-text-secondary);">
            <p>ID: {{ viewer?.document.value?.id }}</p>
            <p v-if="viewer?.document.value?.parser_engine">Parser: {{ viewer.document.value.parser_engine }}</p>
            <p v-if="viewer?.document.value?.parser_config_hash">Config Hash: {{ viewer.document.value.parser_config_hash }}</p>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
