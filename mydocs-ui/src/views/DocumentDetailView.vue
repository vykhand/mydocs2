<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useAppStore } from '@/stores/app'
import { getDocument, getPages, parseSingle, deleteDocument, addTags, removeTag, getDocumentFileUrl } from '@/api/documents'
import type { Document, DocumentPage } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import FileTypeBadge from '@/components/common/FileTypeBadge.vue'
import TagInput from '@/components/common/TagInput.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ParseConfigForm from '@/components/documents/ParseConfigForm.vue'
import { ArrowLeft, Play, Trash2, Eye, Download, Code } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const appStore = useAppStore()

const doc = ref<Document | null>(null)
const pages = ref<DocumentPage[]>([])
const loading = ref(true)
const showDeleteConfirm = ref(false)
const showRawJson = ref(false)
const showParseConfig = ref(false)

const isAdvanced = computed(() => appStore.mode === 'advanced')

const documentId = computed(() => route.params.id as string)

onMounted(async () => {
  loading.value = true
  try {
    doc.value = await getDocument(documentId.value)
    if (doc.value.status === 'parsed') {
      pages.value = await getPages(documentId.value)
    }
  } catch {
    router.push('/documents')
  } finally {
    loading.value = false
  }
})

async function handleParse(configOverride?: Record<string, any>) {
  try {
    const resp = await parseSingle(documentId.value, configOverride)
    toast.success(`Parse ${resp.status}`)
    doc.value = await getDocument(documentId.value)
    if (doc.value.status === 'parsed') {
      pages.value = await getPages(documentId.value)
    }
  } catch { /* interceptor */ }
}

async function handleDelete() {
  try {
    await deleteDocument(documentId.value)
    toast.success('Document deleted')
    router.push('/documents')
  } catch { /* interceptor */ }
}

async function handleAddTags(tags: string[]) {
  if (!doc.value) return
  const currentTags = doc.value.tags || []
  const newTags = tags.filter(t => !currentTags.includes(t))
  if (newTags.length > 0) {
    doc.value = await addTags(documentId.value, newTags)
  }
}

async function handleRemoveTag(tag: string) {
  doc.value = await removeTag(documentId.value, tag)
}

function formatSize(bytes?: number) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(d?: string) {
  if (!d) return '-'
  return new Date(d).toLocaleString()
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <button
      @click="router.push('/documents')"
      class="inline-flex items-center gap-1 text-sm mb-4 hover:opacity-70 transition-opacity"
      style="color: var(--color-text-secondary);"
    >
      <ArrowLeft :size="16" /> Back to Documents
    </button>

    <LoadingSkeleton v-if="loading" :lines="10" />

    <template v-else-if="doc">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-2xl font-semibold mb-2" style="color: var(--color-text-primary);">
            {{ doc.original_file_name }}
          </h1>
          <div class="flex items-center gap-2">
            <FileTypeBadge :file-type="doc.file_type" />
            <StatusBadge :status="doc.status" />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <router-link
            v-if="doc.file_type === 'pdf' || ['jpeg', 'png', 'bmp', 'tiff'].includes(doc.file_type)"
            :to="`/documents/${doc.id}/view`"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
          >
            <Eye :size="16" /> View
          </router-link>
          <a
            :href="getDocumentFileUrl(doc.id)"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
            download
          >
            <Download :size="16" /> Download
          </a>
          <button
            @click="handleParse()"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-white"
            style="background-color: var(--color-accent);"
          >
            <Play :size="16" /> Parse
          </button>
          <button
            @click="showDeleteConfirm = true"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium"
            style="color: var(--color-danger);"
          >
            <Trash2 :size="16" /> Delete
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Content -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Metadata -->
          <section
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Metadata</h2>
            <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div><dt style="color: var(--color-text-secondary);">Size</dt><dd style="color: var(--color-text-primary);">{{ formatSize(doc.file_metadata?.size_bytes) }}</dd></div>
              <div><dt style="color: var(--color-text-secondary);">MIME Type</dt><dd style="color: var(--color-text-primary);">{{ doc.file_metadata?.mime_type || '-' }}</dd></div>
              <div><dt style="color: var(--color-text-secondary);">Pages</dt><dd style="color: var(--color-text-primary);">{{ doc.file_metadata?.page_count ?? '-' }}</dd></div>
              <div><dt style="color: var(--color-text-secondary);">Author</dt><dd style="color: var(--color-text-primary);">{{ doc.file_metadata?.author || '-' }}</dd></div>
              <div><dt style="color: var(--color-text-secondary);">Created</dt><dd style="color: var(--color-text-primary);">{{ formatDate(doc.created_at) }}</dd></div>
              <div><dt style="color: var(--color-text-secondary);">Modified</dt><dd style="color: var(--color-text-primary);">{{ formatDate(doc.modified_at) }}</dd></div>
              <div v-if="doc.file_metadata?.sha256" class="col-span-2">
                <dt style="color: var(--color-text-secondary);">SHA-256</dt>
                <dd class="font-mono text-xs break-all" style="color: var(--color-text-primary);">{{ doc.file_metadata.sha256 }}</dd>
              </div>
            </dl>
          </section>

          <!-- Pages -->
          <section v-if="pages.length > 0"
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Pages ({{ pages.length }})</h2>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <router-link
                v-for="page in pages"
                :key="page.id"
                :to="`/documents/${doc.id}/view?page=${page.page_number}`"
                class="rounded-lg border p-3 text-center hover:shadow-sm transition-shadow"
                style="border-color: var(--color-border); background-color: var(--color-bg-primary);"
              >
                <div class="text-lg font-semibold" style="color: var(--color-text-primary);">{{ page.page_number }}</div>
                <div class="text-xs mt-1 truncate" style="color: var(--color-text-secondary);">
                  {{ page.content?.substring(0, 50) || 'No content' }}
                </div>
              </router-link>
            </div>
          </section>

          <!-- Elements -->
          <section v-if="doc.elements && doc.elements.length > 0"
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Elements ({{ doc.elements.length }})</h2>
            <div class="space-y-1 max-h-64 overflow-y-auto">
              <div
                v-for="el in doc.elements"
                :key="el.id"
                class="flex items-center gap-2 text-xs px-2 py-1.5 rounded"
                style="color: var(--color-text-secondary);"
              >
                <span class="font-mono px-1.5 py-0.5 rounded" style="background-color: var(--color-bg-tertiary);">{{ el.short_id || el.type }}</span>
                <span>Page {{ el.page_number }}</span>
                <span class="capitalize">{{ el.type.replace('_', ' ') }}</span>
              </div>
            </div>
          </section>

          <!-- Advanced: Parse Config -->
          <section v-if="isAdvanced && showParseConfig"
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Parse Configuration</h2>
            <ParseConfigForm @submit="handleParse" />
          </section>

          <!-- Advanced: Raw JSON -->
          <section v-if="isAdvanced && showRawJson"
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Raw JSON</h2>
            <pre class="text-xs overflow-auto max-h-96 font-mono p-3 rounded" style="background-color: var(--color-bg-tertiary); color: var(--color-text-primary);">{{ JSON.stringify(doc, null, 2) }}</pre>
          </section>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Tags -->
          <section
            class="rounded-lg border p-4"
            style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
          >
            <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Tags</h2>
            <div class="flex flex-wrap gap-1.5 mb-3">
              <span
                v-for="tag in doc.tags"
                :key="tag"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium"
                style="background-color: var(--color-bg-tertiary); color: var(--color-text-primary);"
              >
                {{ tag }}
                <button @click="handleRemoveTag(tag)" class="hover:opacity-70">&times;</button>
              </span>
            </div>
            <TagInput :model-value="doc.tags" @update:model-value="handleAddTags" />
          </section>

          <!-- Advanced toggles -->
          <div v-if="isAdvanced" class="space-y-2">
            <button
              @click="showParseConfig = !showParseConfig"
              class="w-full text-left px-3 py-2 rounded-lg text-sm border"
              style="border-color: var(--color-border); color: var(--color-text-primary);"
            >
              <Play :size="14" class="inline mr-1.5" /> Parse Config
            </button>
            <button
              @click="showRawJson = !showRawJson"
              class="w-full text-left px-3 py-2 rounded-lg text-sm border"
              style="border-color: var(--color-border); color: var(--color-text-primary);"
            >
              <Code :size="14" class="inline mr-1.5" /> Raw JSON
            </button>
          </div>
        </div>
      </div>
    </template>

    <ConfirmDialog
      v-if="showDeleteConfirm"
      title="Delete Document"
      message="Are you sure? This will permanently delete the document and all its pages."
      confirm-label="Delete"
      variant="danger"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
