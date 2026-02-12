<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { useAppStore } from '@/stores/app'
import CaseCard from '@/components/cases/CaseCard.vue'
import CreateCaseDialog from '@/components/cases/CreateCaseDialog.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const casesStore = useCasesStore()
const appStore = useAppStore()
const showCreateDialog = ref(false)

onMounted(() => {
  casesStore.fetchCases()
})

function onCaseCreated() {
  showCreateDialog.value = false
  casesStore.fetchCases()
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold" style="color: var(--color-text-primary);">Cases</h1>
      <button
        @click="showCreateDialog = true"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white"
        style="background-color: var(--color-accent);"
      >
        <Plus :size="16" />
        New Case
      </button>
    </div>

    <!-- Cases grid -->
    <LoadingSkeleton v-if="casesStore.loading" />
    <div v-else-if="casesStore.cases.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <CaseCard
        v-for="c in casesStore.cases"
        :key="c.id"
        :case-data="c"
        @click="router.push(`/cases/${c.id}`)"
      />
    </div>
    <EmptyState
      v-else
      title="No cases yet"
      message="Create your first case to start organizing documents."
    />

    <CreateCaseDialog
      v-if="showCreateDialog"
      @close="showCreateDialog = false"
      @created="onCaseCreated"
    />
  </div>
</template>
