<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useDocumentsStore } from '@/stores/documents'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import { Eye, Play, Trash2 } from 'lucide-vue-next'
import { deleteDocument, parseSingle } from '@/api/documents'
import { useToast } from 'vue-toastification'
import { ref } from 'vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const docsStore = useDocumentsStore()
const toast = useToast()
const deleteTarget = ref<string | null>(null)

function formatDate(d?: string) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

async function handleParse(id: string) {
  try {
    await parseSingle(id)
    toast.success('Parse started')
    docsStore.fetchDocuments()
  } catch { /* interceptor */ }
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteDocument(deleteTarget.value)
    toast.success('Document deleted')
    deleteTarget.value = null
    docsStore.fetchDocuments()
  } catch { /* interceptor */ }
}

const allSelected = () => docsStore.documents.every(d => docsStore.selectedIds.has(d.id))

function toggleAll() {
  if (allSelected()) {
    docsStore.clearSelection()
  } else {
    docsStore.selectAll()
  }
}
</script>

<template>
  <div class="rounded-lg border overflow-x-auto" style="border-color: var(--color-border);">
    <table class="w-full text-sm">
      <thead>
        <tr style="background-color: var(--color-bg-secondary);">
          <th class="w-10 px-3 py-3">
            <input type="checkbox" :checked="allSelected()" @change="toggleAll" class="rounded" />
          </th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Name</th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Type</th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Status</th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Tags</th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Pages</th>
          <th class="text-left px-3 py-3 font-medium" style="color: var(--color-text-secondary);">Created</th>
          <th class="w-24 px-3 py-3" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="doc in docsStore.documents"
          :key="doc.id"
          class="border-t cursor-pointer hover:opacity-90 transition-opacity"
          style="border-color: var(--color-border);"
          @click="router.push(`/documents/${doc.id}`)"
        >
          <td class="px-3 py-3" @click.stop>
            <input
              type="checkbox"
              :checked="docsStore.selectedIds.has(doc.id)"
              @change="docsStore.toggleSelect(doc.id)"
              class="rounded"
            />
          </td>
          <td class="px-3 py-3 font-medium" style="color: var(--color-text-primary);">
            {{ doc.original_file_name }}
          </td>
          <td class="px-3 py-3"><FileTypeBadge :file-type="doc.file_type" /></td>
          <td class="px-3 py-3"><StatusBadge :status="doc.status" /></td>
          <td class="px-3 py-3">
            <div class="flex flex-wrap gap-1">
              <span
                v-for="tag in doc.tags?.slice(0, 3)"
                :key="tag"
                class="px-1.5 py-0.5 rounded text-xs"
                style="background-color: var(--color-bg-tertiary); color: var(--color-text-secondary);"
              >
                {{ tag }}
              </span>
              <span
                v-if="(doc.tags?.length || 0) > 3"
                class="text-xs"
                style="color: var(--color-text-secondary);"
              >
                +{{ doc.tags!.length - 3 }}
              </span>
            </div>
          </td>
          <td class="px-3 py-3" style="color: var(--color-text-secondary);">
            {{ doc.file_metadata?.page_count ?? '-' }}
          </td>
          <td class="px-3 py-3" style="color: var(--color-text-secondary);">
            {{ formatDate(doc.created_at) }}
          </td>
          <td class="px-3 py-3" @click.stop>
            <div class="flex items-center gap-1">
              <button
                @click="router.push(`/documents/${doc.id}`)"
                class="p-1.5 rounded hover:opacity-70"
                style="color: var(--color-text-secondary);"
                title="View"
              >
                <Eye :size="16" />
              </button>
              <button
                @click="handleParse(doc.id)"
                class="p-1.5 rounded hover:opacity-70"
                style="color: var(--color-text-secondary);"
                title="Parse"
              >
                <Play :size="16" />
              </button>
              <button
                @click="deleteTarget = doc.id"
                class="p-1.5 rounded hover:opacity-70"
                style="color: var(--color-danger);"
                title="Delete"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <ConfirmDialog
    v-if="deleteTarget"
    title="Delete Document"
    message="Are you sure you want to delete this document? This action cannot be undone."
    confirm-label="Delete"
    variant="danger"
    @confirm="handleDelete"
    @cancel="deleteTarget = null"
  />
</template>
