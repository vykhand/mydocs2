<script setup lang="ts">
import { ref } from 'vue'
import { Upload } from 'lucide-vue-next'

defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  files: [files: File[]]
}>()

const dragOver = ref(false)
const fileInput = ref<HTMLInputElement>()
const folderInput = ref<HTMLInputElement>()

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files) {
    emit('files', Array.from(e.dataTransfer.files))
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    emit('files', Array.from(input.files))
    input.value = ''
  }
}
</script>

<template>
  <div
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
    @click="fileInput?.click()"
    class="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all"
    :style="{
      borderColor: dragOver ? 'var(--color-accent)' : 'var(--color-border)',
      backgroundColor: dragOver ? 'var(--color-bg-tertiary)' : 'var(--color-bg-secondary)',
      opacity: disabled ? '0.5' : '1',
      pointerEvents: disabled ? 'none' : 'auto',
    }"
  >
    <Upload :size="40" class="mx-auto mb-3" style="color: var(--color-text-secondary);" />
    <p class="text-sm font-medium mb-1" style="color: var(--color-text-primary);">
      Drop files here or click to browse
    </p>
    <p class="text-xs" style="color: var(--color-text-secondary);">
      PDF, DOCX, XLSX, PPTX, TXT, and image files
    </p>
    <div class="mt-3">
      <button
        @click.stop="folderInput?.click()"
        class="text-xs font-medium px-3 py-1.5 rounded-md border transition-colors"
        style="border-color: var(--color-border); color: var(--color-text-secondary);"
      >
        Select Folder
      </button>
    </div>
    <input ref="fileInput" type="file" multiple class="hidden" @change="onFileSelect" />
    <input ref="folderInput" type="file" multiple webkitdirectory class="hidden" @change="onFileSelect" />
  </div>
</template>
