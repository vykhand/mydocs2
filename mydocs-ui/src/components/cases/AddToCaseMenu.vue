<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCasesStore } from '@/stores/cases'
import { addDocumentsToCase } from '@/api/cases'
import { useToast } from 'vue-toastification'
import { Briefcase, ChevronDown } from 'lucide-vue-next'

const props = defineProps<{
  documentIds: string[]
}>()

const emit = defineEmits<{
  added: []
}>()

const casesStore = useCasesStore()
const toast = useToast()
const open = ref(false)

onMounted(() => {
  if (!casesStore.cases.length) {
    casesStore.fetchCases()
  }
})

async function addToCase(caseId: string) {
  try {
    await addDocumentsToCase(caseId, props.documentIds)
    toast.success('Documents added to case')
    open.value = false
    emit('added')
  } catch { /* interceptor */ }
}
</script>

<template>
  <div class="relative">
    <button
      @click="open = !open"
      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border"
      style="border-color: var(--color-border); color: var(--color-text-primary);"
    >
      <Briefcase :size="14" />
      Add to Case
      <ChevronDown :size="12" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 mt-1 w-56 rounded-lg shadow-lg border overflow-hidden z-20"
      style="background-color: var(--color-bg-primary); border-color: var(--color-border);"
    >
      <div v-if="casesStore.cases.length" class="max-h-48 overflow-y-auto">
        <button
          v-for="c in casesStore.cases"
          :key="c.id"
          @click="addToCase(c.id)"
          class="w-full px-3 py-2 text-left text-sm hover:opacity-80 flex items-center gap-2"
          style="color: var(--color-text-primary);"
        >
          <Briefcase :size="14" style="color: var(--color-text-secondary);" />
          <span class="truncate">{{ c.name }}</span>
        </button>
      </div>
      <p v-else class="px-3 py-2 text-xs" style="color: var(--color-text-secondary);">
        No cases yet. Create one first.
      </p>
    </div>

    <!-- Click outside handler -->
    <Teleport to="body">
      <div v-if="open" class="fixed inset-0 z-10" @click="open = false" />
    </Teleport>
  </div>
</template>
