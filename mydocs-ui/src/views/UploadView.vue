<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useAppStore } from '@/stores/app'
import { uploadAndIngest, ingestFromPath } from '@/api/documents'
import DropZone from '@/components/upload/DropZone.vue'
import FileQueue from '@/components/upload/FileQueue.vue'
import UploadProgress from '@/components/upload/UploadProgress.vue'
import TagInput from '@/components/common/TagInput.vue'

const router = useRouter()
const toast = useToast()
const appStore = useAppStore()

const files = ref<File[]>([])
const tags = ref<string[]>([])
const storageMode = ref('managed')
const parseAfterUpload = ref(false)
const recursive = ref(true)
const serverPath = ref('')
const uploading = ref(false)
const progress = ref(0)
const result = ref<{ documents: any[]; skipped: any[] } | null>(null)

const isAdvanced = computed(() => appStore.mode === 'advanced')

function addFiles(newFiles: File[]) {
  const existing = new Set(files.value.map(f => f.name + f.size))
  newFiles.forEach(f => {
    if (!existing.has(f.name + f.size)) {
      files.value.push(f)
    }
  })
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

async function upload() {
  if (files.value.length === 0) return
  uploading.value = true
  progress.value = 0
  result.value = null
  try {
    const resp = await uploadAndIngest(
      files.value,
      tags.value,
      storageMode.value,
      parseAfterUpload.value,
      (pct) => { progress.value = pct },
    )
    result.value = resp
    toast.success(`Ingested ${resp.documents.length} document(s)`)
    files.value = []
  } catch {
    // Error handled by interceptor
  } finally {
    uploading.value = false
  }
}

async function ingestServer() {
  if (!serverPath.value.trim()) return
  uploading.value = true
  try {
    const resp = await ingestFromPath({
      source: serverPath.value,
      storage_mode: storageMode.value,
      tags: tags.value,
      recursive: recursive.value,
    })
    result.value = resp
    toast.success(`Ingested ${resp.documents.length} document(s)`)
    serverPath.value = ''
  } catch {
    // Error handled by interceptor
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <h1 class="text-2xl font-semibold" style="color: var(--color-text-primary);">Upload Documents</h1>

    <DropZone @files="addFiles" :disabled="uploading" />

    <FileQueue v-if="files.length > 0" :files="files" @remove="removeFile" />

    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text-secondary);">Tags</label>
        <TagInput v-model="tags" />
      </div>

      <label class="flex items-center gap-2 text-sm" style="color: var(--color-text-primary);">
        <input type="checkbox" v-model="parseAfterUpload" class="rounded" />
        Parse after upload
      </label>

      <template v-if="isAdvanced">
        <div>
          <label class="block text-sm font-medium mb-1.5" style="color: var(--color-text-secondary);">Storage Mode</label>
          <select
            v-model="storageMode"
            class="rounded-lg border px-3 py-2 text-sm w-full"
            style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
          >
            <option value="managed">Managed</option>
            <option value="external">External</option>
          </select>
        </div>

        <div
          class="p-4 rounded-lg border space-y-3"
          style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
        >
          <h3 class="text-sm font-medium" style="color: var(--color-text-primary);">Ingest from Server Path</h3>
          <div class="flex gap-2">
            <input
              v-model="serverPath"
              placeholder="/path/to/files"
              class="flex-1 rounded-lg border px-3 py-2 text-sm"
              style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
            />
            <button
              @click="ingestServer"
              :disabled="!serverPath.trim() || uploading"
              class="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style="background-color: var(--color-accent);"
            >
              Ingest
            </button>
          </div>
          <label class="flex items-center gap-2 text-sm" style="color: var(--color-text-primary);">
            <input type="checkbox" v-model="recursive" class="rounded" />
            Recursive
          </label>
        </div>
      </template>
    </div>

    <button
      @click="upload"
      :disabled="files.length === 0 || uploading"
      class="w-full py-3 rounded-lg text-sm font-medium text-white disabled:opacity-50 transition-colors"
      style="background-color: var(--color-accent);"
    >
      {{ uploading ? 'Uploading...' : `Upload ${files.length} file(s)` }}
    </button>

    <UploadProgress v-if="uploading || result" :progress="progress" :result="result" :uploading="uploading" />
  </div>
</template>
