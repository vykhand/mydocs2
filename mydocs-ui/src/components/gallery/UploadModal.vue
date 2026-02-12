<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import DropZone from '@/components/upload/DropZone.vue'
import FileQueue from '@/components/upload/FileQueue.vue'
import UploadProgress from '@/components/upload/UploadProgress.vue'
import TagInput from '@/components/common/TagInput.vue'
import { uploadAndIngest } from '@/api/documents'
import { useDocumentsStore } from '@/stores/documents'
import { useToast } from 'vue-toastification'

const emit = defineEmits<{
  close: []
}>()

const docsStore = useDocumentsStore()
const toast = useToast()
const files = ref<File[]>([])
const tags = ref<string[]>([])
const uploading = ref(false)
const progress = ref(0)

function addFiles(newFiles: File[]) {
  files.value.push(...newFiles)
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

async function handleUpload() {
  if (!files.value.length) return
  uploading.value = true
  progress.value = 0
  try {
    const resp = await uploadAndIngest(
      files.value,
      tags.value,
      'managed',
      false,
      (pct) => { progress.value = pct },
    )
    toast.success(`Uploaded ${resp.documents.length} document(s)`)
    files.value = []
    docsStore.fetchDocuments()
    emit('close')
  } catch {
    /* interceptor handles errors */
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div
        class="relative z-10 w-full max-w-2xl mx-4 rounded-xl shadow-xl overflow-hidden"
        style="background-color: var(--color-bg-primary);"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b" style="border-color: var(--color-border);">
          <h2 class="text-lg font-semibold" style="color: var(--color-text-primary);">Upload Documents</h2>
          <button @click="emit('close')" class="p-1 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
            <X :size="20" />
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          <DropZone @files-added="addFiles" />

          <div v-if="files.length" class="space-y-3">
            <FileQueue :files="files" @remove="removeFile" />
            <div>
              <p class="text-sm font-medium mb-1" style="color: var(--color-text-primary);">Tags</p>
              <TagInput v-model="tags" />
            </div>
          </div>

          <UploadProgress v-if="uploading" :progress="progress" />
        </div>

        <!-- Footer -->
        <div class="flex justify-end gap-3 px-6 py-4 border-t" style="border-color: var(--color-border);">
          <button
            @click="emit('close')"
            class="px-4 py-2 rounded-lg text-sm border"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
          >
            Cancel
          </button>
          <button
            @click="handleUpload"
            :disabled="!files.length || uploading"
            class="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style="background-color: var(--color-accent);"
          >
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
