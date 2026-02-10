<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentViewer } from '@/composables/useDocumentViewer'
import DocumentViewer from '@/components/viewer/DocumentViewer.vue'
import ViewerToolbar from '@/components/viewer/ViewerToolbar.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'

const route = useRoute()
const router = useRouter()

const documentId = computed(() => route.params.id as string)
const initialPage = computed(() => Number(route.query.page) || 1)

const viewer = useDocumentViewer(documentId.value, initialPage.value)
</script>

<template>
  <div class="h-full flex flex-col -m-4 md:-m-6">
    <ViewerToolbar
      :current-page="viewer.currentPage.value"
      :total-pages="viewer.totalPages.value"
      :zoom="viewer.zoom.value"
      :document="viewer.document.value"
      @go-to-page="viewer.goToPage"
      @prev-page="viewer.prevPage"
      @next-page="viewer.nextPage"
      @set-zoom="viewer.setZoom"
      @fit-width="viewer.fitToWidth"
      @fit-page="viewer.fitToPage"
      @close="router.push(`/documents/${documentId}`)"
    />

    <div class="flex-1 overflow-hidden">
      <LoadingSkeleton v-if="viewer.loading.value" :lines="10" class="p-8" />
      <DocumentViewer
        v-else-if="viewer.document.value"
        :document="viewer.document.value"
        :current-page="viewer.currentPage.value"
        :zoom="viewer.zoom.value"
        :file-url="viewer.fileUrl"
        @go-to-page="viewer.goToPage"
      />
    </div>
  </div>
</template>
