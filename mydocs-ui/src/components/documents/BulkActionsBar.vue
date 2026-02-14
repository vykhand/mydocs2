<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useToast } from 'vue-toastification'
import { batchParse, deleteDocument, addTags } from '@/api/documents'
import TagInput from '@/components/common/TagInput.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { Play, Tag, Trash2, X } from 'lucide-vue-next'
import AddToCaseMenu from '@/components/cases/AddToCaseMenu.vue'

const docsStore = useDocumentsStore()
const toast = useToast()
const showTagModal = ref(false)
const showDeleteConfirm = ref(false)
const bulkTags = ref<string[]>([])

async function bulkParse() {
  const ids = Array.from(docsStore.selectedIds)
  try {
    const resp = await batchParse(ids)
    toast.success(`Queued ${resp.queued} document(s) for parsing`)
    docsStore.clearSelection()
    docsStore.fetchDocuments()
  } catch { /* interceptor */ }
}

async function bulkAddTags() {
  const ids = Array.from(docsStore.selectedIds)
  for (const id of ids) {
    await addTags(id, bulkTags.value)
  }
  toast.success(`Tags added to ${ids.length} document(s)`)
  bulkTags.value = []
  showTagModal.value = false
  docsStore.clearSelection()
  docsStore.fetchDocuments()
}

async function bulkDelete() {
  const ids = Array.from(docsStore.selectedIds)
  for (const id of ids) {
    await deleteDocument(id)
  }
  toast.success(`Deleted ${ids.length} document(s)`)
  showDeleteConfirm.value = false
  docsStore.clearSelection()
  docsStore.fetchDocuments()
}
</script>

<template>
  <div
    class="flex items-center gap-3 px-4 py-2.5 rounded-lg"
    style="background-color: var(--color-bg-secondary); border: 1px solid var(--color-border);"
  >
    <span class="text-sm font-medium" style="color: var(--color-text-primary);">
      {{ docsStore.selectedIds.size }} selected
    </span>
    <div class="flex items-center gap-2 ml-auto">
      <button
        @click="bulkParse"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border"
        style="border-color: var(--color-border); color: var(--color-text-primary);"
      >
        <Play :size="14" /> Parse
      </button>
      <button
        @click="showTagModal = true"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border"
        style="border-color: var(--color-border); color: var(--color-text-primary);"
      >
        <Tag :size="14" /> Add Tags
      </button>
      <AddToCaseMenu :document-ids="Array.from(docsStore.selectedIds)" />
      <button
        @click="showDeleteConfirm = true"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium"
        style="color: var(--color-danger);"
      >
        <Trash2 :size="14" /> Delete
      </button>
      <button
        @click="docsStore.clearSelection()"
        class="p-1 rounded hover:opacity-70"
        style="color: var(--color-text-secondary);"
      >
        <X :size="16" />
      </button>
    </div>
  </div>

  <!-- Tag Modal -->
  <Teleport to="body">
    <div v-if="showTagModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="showTagModal = false" />
      <div class="relative z-10 w-full max-w-md mx-4 p-6 rounded-xl shadow-xl" style="background-color: var(--color-bg-primary);">
        <h3 class="text-lg font-semibold mb-4" style="color: var(--color-text-primary);">Add Tags</h3>
        <TagInput v-model="bulkTags" />
        <div class="flex justify-end gap-3 mt-4">
          <button @click="showTagModal = false" class="px-4 py-2 rounded-lg text-sm border" style="border-color: var(--color-border); color: var(--color-text-primary);">Cancel</button>
          <button @click="bulkAddTags" class="px-4 py-2 rounded-lg text-sm font-medium text-white" style="background-color: var(--color-accent);">Add Tags</button>
        </div>
      </div>
    </div>
  </Teleport>

  <ConfirmDialog
    v-if="showDeleteConfirm"
    title="Delete Documents"
    :message="`Delete ${docsStore.selectedIds.size} selected document(s)? This cannot be undone.`"
    confirm-label="Delete All"
    variant="danger"
    @confirm="bulkDelete"
    @cancel="showDeleteConfirm = false"
  />
</template>
