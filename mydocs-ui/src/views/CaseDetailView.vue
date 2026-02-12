<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { getCaseDocuments, deleteCase, removeDocumentFromCase } from '@/api/cases'
import { useToast } from 'vue-toastification'
import CaseHeader from '@/components/cases/CaseHeader.vue'
import DocumentTable from '@/components/documents/DocumentTable.vue'
import DocumentGrid from '@/components/gallery/DocumentGrid.vue'
import AddToCaseMenu from '@/components/cases/AddToCaseMenu.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { Document } from '@/types'

const route = useRoute()
const router = useRouter()
const casesStore = useCasesStore()
const toast = useToast()

const caseId = route.params.id as string
const documents = ref<Document[]>([])
const docTotal = ref(0)
const loadingDocs = ref(false)
const showDeleteConfirm = ref(false)
const activeSubTab = ref('documents')

async function loadDocs() {
  loadingDocs.value = true
  try {
    const resp = await getCaseDocuments(caseId)
    documents.value = resp.documents
    docTotal.value = resp.total
  } finally {
    loadingDocs.value = false
  }
}

async function handleDeleteCase() {
  try {
    await deleteCase(caseId)
    toast.success('Case deleted')
    router.push('/cases')
  } catch { /* interceptor */ }
}

async function handleRemoveDocument(docId: string) {
  try {
    await removeDocumentFromCase(caseId, docId)
    toast.success('Document removed from case')
    loadDocs()
    casesStore.fetchCase(caseId)
  } catch { /* interceptor */ }
}

onMounted(() => {
  casesStore.fetchCase(caseId)
  loadDocs()
})
</script>

<template>
  <div class="space-y-4">
    <LoadingSkeleton v-if="casesStore.loading && !casesStore.currentCase" />

    <template v-else-if="casesStore.currentCase">
      <CaseHeader
        :case-data="casesStore.currentCase"
        @delete="showDeleteConfirm = true"
        @updated="casesStore.fetchCase(caseId)"
      />

      <!-- Sub-navigation tabs -->
      <div class="flex gap-4 border-b" style="border-color: var(--color-border);">
        <button
          @click="activeSubTab = 'documents'"
          class="pb-2 text-sm font-medium border-b-2 transition-colors"
          :style="{
            color: activeSubTab === 'documents' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
            borderBottomColor: activeSubTab === 'documents' ? 'var(--color-accent)' : 'transparent',
          }"
        >
          Documents ({{ docTotal }})
        </button>
        <button
          disabled
          class="pb-2 text-sm font-medium opacity-50 cursor-not-allowed"
          style="color: var(--color-text-secondary);"
        >
          Extraction Results (coming soon)
        </button>
      </div>

      <!-- Documents sub-tab -->
      <div v-if="activeSubTab === 'documents'">
        <LoadingSkeleton v-if="loadingDocs" />
        <DocumentGrid v-else-if="documents.length" :documents="documents" />
        <div v-else class="text-center py-12">
          <p class="text-sm" style="color: var(--color-text-secondary);">
            No documents in this case yet.
          </p>
        </div>
      </div>
    </template>

    <ConfirmDialog
      v-if="showDeleteConfirm"
      title="Delete Case"
      message="Are you sure you want to delete this case? Documents will not be deleted."
      confirm-label="Delete"
      variant="danger"
      @confirm="handleDeleteCase"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
