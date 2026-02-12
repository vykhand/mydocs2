<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import DocumentCard from '@/components/documents/DocumentCard.vue'
import DocumentTable from '@/components/documents/DocumentTable.vue'
import type { Document } from '@/types'

defineProps<{
  documents: Document[]
}>()

const appStore = useAppStore()
</script>

<template>
  <!-- Grid mode -->
  <div v-if="appStore.galleryViewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
    <DocumentCard
      v-for="doc in documents"
      :key="doc.id"
      :document="doc"
    />
  </div>

  <!-- List/table mode -->
  <DocumentTable v-else />
</template>
