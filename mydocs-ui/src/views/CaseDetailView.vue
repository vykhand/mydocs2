<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { getCaseDocuments, deleteCase, removeDocumentFromCase, addDocumentsToCase } from '@/api/cases'
import { listDocuments } from '@/api/documents'
import { useToast } from 'vue-toastification'
import CaseHeader from '@/components/cases/CaseHeader.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import { Trash2, Plus, Search } from 'lucide-vue-next'
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

// Add Documents modal state
const showAddDocsModal = ref(false)
const addDocsSearch = ref('')
const addDocsResults = ref<Document[]>([])
const addDocsLoading = ref(false)
const selectedDocIds = ref<Set<string>>(new Set())

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

async function openAddDocsModal() {
  showAddDocsModal.value = true
  addDocsSearch.value = ''
  selectedDocIds.value = new Set()
  await searchAvailableDocs()
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function onAddDocsSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(searchAvailableDocs, 300)
}

async function searchAvailableDocs() {
  addDocsLoading.value = true
  try {
    const resp = await listDocuments({ search: addDocsSearch.value || undefined, page_size: 50 })
    const caseDocIds = new Set(documents.value.map(d => d.id))
    addDocsResults.value = resp.documents.filter(d => !caseDocIds.has(d.id))
  } finally {
    addDocsLoading.value = false
  }
}

function toggleDocSelection(docId: string) {
  const s = new Set(selectedDocIds.value)
  if (s.has(docId)) s.delete(docId)
  else s.add(docId)
  selectedDocIds.value = s
}

async function confirmAddDocs() {
  if (!selectedDocIds.value.size) return
  try {
    await addDocumentsToCase(caseId, Array.from(selectedDocIds.value))
    toast.success(`Added ${selectedDocIds.value.size} document(s) to case`)
    showAddDocsModal.value = false
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
        <div class="flex justify-end mb-3">
          <button
            @click="openAddDocsModal"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium"
            style="background-color: var(--color-accent); color: white;"
          >
            <Plus :size="14" />
            Add Documents
          </button>
        </div>

        <LoadingSkeleton v-if="loadingDocs" />

        <div v-else-if="documents.length" class="space-y-2">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="flex items-center gap-3 px-4 py-3 rounded-lg border cursor-pointer hover:shadow-sm transition-shadow"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
            @click="$router.push(`/doc/${doc.id}`)"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate" style="color: var(--color-text-primary);">
                {{ doc.original_file_name }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <FileTypeBadge :file-type="doc.file_type" />
                <StatusBadge :status="doc.status" />
              </div>
            </div>
            <button
              @click.stop="handleRemoveDocument(doc.id)"
              class="p-1.5 rounded-md hover:opacity-80 shrink-0"
              style="color: var(--color-danger);"
              title="Remove from case"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </div>

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

    <!-- Add Documents Modal -->
    <Teleport to="body">
      <div v-if="showAddDocsModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="fixed inset-0 bg-black/50" @click="showAddDocsModal = false" />
        <div
          class="relative w-full max-w-lg max-h-[80vh] flex flex-col rounded-xl shadow-xl border"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border);"
        >
          <div class="flex items-center justify-between px-5 py-4 border-b" style="border-color: var(--color-border);">
            <h3 class="text-sm font-semibold" style="color: var(--color-text-primary);">Add Documents to Case</h3>
            <button @click="showAddDocsModal = false" class="text-lg leading-none" style="color: var(--color-text-secondary);">&times;</button>
          </div>

          <div class="px-5 py-3 border-b" style="border-color: var(--color-border);">
            <div class="relative">
              <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2" style="color: var(--color-text-secondary);" />
              <input
                v-model="addDocsSearch"
                @input="onAddDocsSearchInput"
                placeholder="Search documents..."
                class="w-full pl-9 pr-3 py-2 text-sm rounded-md border outline-none"
                style="border-color: var(--color-border); background-color: var(--color-bg-secondary); color: var(--color-text-primary);"
              />
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-5 py-3 min-h-0">
            <div v-if="addDocsLoading" class="flex justify-center py-8">
              <div class="animate-spin w-5 h-5 border-2 border-t-transparent rounded-full" style="border-color: var(--color-accent); border-top-color: transparent;" />
            </div>
            <div v-else-if="addDocsResults.length" class="space-y-1">
              <label
                v-for="doc in addDocsResults"
                :key="doc.id"
                class="flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer hover:opacity-80"
                :style="{ backgroundColor: selectedDocIds.has(doc.id) ? 'var(--color-bg-tertiary)' : 'transparent' }"
              >
                <input
                  type="checkbox"
                  :checked="selectedDocIds.has(doc.id)"
                  @change="toggleDocSelection(doc.id)"
                  class="rounded"
                />
                <div class="flex-1 min-w-0">
                  <p class="text-sm truncate" style="color: var(--color-text-primary);">{{ doc.original_file_name }}</p>
                  <div class="flex items-center gap-2 mt-0.5">
                    <FileTypeBadge :file-type="doc.file_type" />
                    <StatusBadge :status="doc.status" />
                  </div>
                </div>
              </label>
            </div>
            <p v-else class="text-center py-8 text-sm" style="color: var(--color-text-secondary);">
              No documents found.
            </p>
          </div>

          <div class="flex items-center justify-end gap-2 px-5 py-4 border-t" style="border-color: var(--color-border);">
            <button
              @click="showAddDocsModal = false"
              class="px-3 py-1.5 text-xs font-medium rounded-md border"
              style="border-color: var(--color-border); color: var(--color-text-secondary);"
            >
              Cancel
            </button>
            <button
              @click="confirmAddDocs"
              :disabled="!selectedDocIds.size"
              class="px-3 py-1.5 text-xs font-medium rounded-md disabled:opacity-50"
              style="background-color: var(--color-accent); color: white;"
            >
              Add {{ selectedDocIds.size || '' }} Document{{ selectedDocIds.size === 1 ? '' : 's' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
