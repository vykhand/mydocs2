<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import DocumentFilters from '@/components/documents/DocumentFilters.vue'
import DocumentTable from '@/components/documents/DocumentTable.vue'
import BulkActionsBar from '@/components/documents/BulkActionsBar.vue'
import PaginationBar from '@/components/common/PaginationBar.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { FileText, Upload } from 'lucide-vue-next'

const docsStore = useDocumentsStore()
const appStore = useAppStore()

onMounted(() => {
  docsStore.fetchDocuments()
})

watch(
  () => [docsStore.filters.status, docsStore.filters.file_type, docsStore.filters.tags, docsStore.filters.search, docsStore.filters.sort_by, docsStore.filters.sort_order],
  () => {
    docsStore.filters.page = 1
    docsStore.fetchDocuments()
  },
)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold" style="color: var(--color-text-primary);">Documents</h1>
      <router-link
        to="/upload"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
        style="background-color: var(--color-accent);"
      >
        <Upload :size="16" />
        Upload
      </router-link>
    </div>

    <DocumentFilters />

    <BulkActionsBar v-if="docsStore.selectedIds.size > 0" />

    <LoadingSkeleton v-if="docsStore.loading" :lines="8" />

    <template v-else-if="docsStore.documents.length > 0">
      <DocumentTable />
      <PaginationBar
        :page="docsStore.filters.page!"
        :page-size="docsStore.filters.page_size!"
        :total="docsStore.total"
        @update:page="(p) => { docsStore.filters.page = p; docsStore.fetchDocuments() }"
        @update:page-size="(s) => { docsStore.filters.page_size = s; docsStore.filters.page = 1; docsStore.fetchDocuments() }"
      />
    </template>

    <EmptyState
      v-else
      :icon="FileText"
      title="No documents yet"
      description="Upload your first file to get started."
      action-label="Upload Files"
      @action="$router.push('/upload')"
    />
  </div>
</template>
