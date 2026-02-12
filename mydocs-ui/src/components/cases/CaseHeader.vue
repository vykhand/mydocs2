<script setup lang="ts">
import { ref } from 'vue'
import type { Case } from '@/types'
import { updateCase } from '@/api/cases'
import { useToast } from 'vue-toastification'
import { Pencil, Trash2, ArrowLeft } from 'lucide-vue-next'

const props = defineProps<{
  caseData: Case
}>()

const emit = defineEmits<{
  delete: []
  updated: []
}>()

const toast = useToast()
const editing = ref(false)
const editName = ref(props.caseData.name)
const editDescription = ref(props.caseData.description || '')

async function saveEdit() {
  try {
    await updateCase(props.caseData.id, {
      name: editName.value,
      description: editDescription.value || undefined,
    })
    toast.success('Case updated')
    editing.value = false
    emit('updated')
  } catch { /* interceptor */ }
}

function formatDate(d?: string) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}
</script>

<template>
  <div>
    <div class="flex items-center gap-2 mb-2">
      <router-link to="/cases" class="p-1 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
        <ArrowLeft :size="18" />
      </router-link>
    </div>

    <template v-if="!editing">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-xl font-semibold" style="color: var(--color-text-primary);">{{ caseData.name }}</h1>
          <p v-if="caseData.description" class="text-sm mt-1" style="color: var(--color-text-secondary);">
            {{ caseData.description }}
          </p>
          <div class="flex items-center gap-3 mt-2 text-xs" style="color: var(--color-text-secondary);">
            <span>{{ caseData.document_ids?.length || 0 }} documents</span>
            <span>Created {{ formatDate(caseData.created_at) }}</span>
            <span>Modified {{ formatDate(caseData.modified_at) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <button
            @click="editing = true; editName = caseData.name; editDescription = caseData.description || ''"
            class="p-1.5 rounded hover:opacity-70"
            style="color: var(--color-text-secondary);"
            title="Edit"
          >
            <Pencil :size="16" />
          </button>
          <button
            @click="emit('delete')"
            class="p-1.5 rounded hover:opacity-70"
            style="color: var(--color-danger);"
            title="Delete"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="space-y-3">
        <input
          v-model="editName"
          class="w-full px-3 py-2 rounded-lg border text-sm"
          style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
          placeholder="Case name"
        />
        <textarea
          v-model="editDescription"
          class="w-full px-3 py-2 rounded-lg border text-sm resize-none"
          style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
          rows="3"
          placeholder="Description (optional)"
        />
        <div class="flex gap-2">
          <button
            @click="saveEdit"
            class="px-3 py-1.5 rounded-lg text-sm font-medium text-white"
            style="background-color: var(--color-accent);"
          >
            Save
          </button>
          <button
            @click="editing = false"
            class="px-3 py-1.5 rounded-lg text-sm border"
            style="border-color: var(--color-border); color: var(--color-text-primary);"
          >
            Cancel
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
