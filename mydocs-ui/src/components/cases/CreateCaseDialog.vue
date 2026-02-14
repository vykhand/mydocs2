<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { createCase } from '@/api/cases'
import { useToast } from 'vue-toastification'

const emit = defineEmits<{
  close: []
  created: []
}>()

const toast = useToast()
const name = ref('')
const description = ref('')
const submitting = ref(false)

async function handleSubmit() {
  if (!name.value.trim()) return
  submitting.value = true
  try {
    await createCase({ name: name.value.trim(), description: description.value.trim() || undefined })
    toast.success('Case created')
    emit('created')
  } catch { /* interceptor */ }
  finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div class="relative z-10 w-full max-w-md mx-4 rounded-xl shadow-xl" style="background-color: var(--color-bg-primary);">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b" style="border-color: var(--color-border);">
          <h2 class="text-lg font-semibold" style="color: var(--color-text-primary);">New Case</h2>
          <button @click="emit('close')" class="p-1 rounded hover:opacity-70" style="color: var(--color-text-secondary);">
            <X :size="20" />
          </button>
        </div>

        <!-- Form -->
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1" style="color: var(--color-text-primary);">Name</label>
            <input
              v-model="name"
              class="w-full px-3 py-2 rounded-lg border text-sm"
              style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
              placeholder="Case name"
              maxlength="200"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1" style="color: var(--color-text-primary);">Description</label>
            <textarea
              v-model="description"
              class="w-full px-3 py-2 rounded-lg border text-sm resize-none"
              style="background-color: var(--color-bg-tertiary); border-color: var(--color-border); color: var(--color-text-primary);"
              rows="3"
              placeholder="Optional description"
            />
          </div>
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
            @click="handleSubmit"
            :disabled="!name.trim() || submitting"
            class="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style="background-color: var(--color-accent);"
          >
            {{ submitting ? 'Creating...' : 'Create Case' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
