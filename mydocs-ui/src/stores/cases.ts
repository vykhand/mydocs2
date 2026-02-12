import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Case } from '@/types'
import { listCases, getCase as getCaseApi } from '@/api/cases'

export const useCasesStore = defineStore('cases', () => {
  const cases = ref<Case[]>([])
  const currentCase = ref<Case | null>(null)
  const total = ref(0)
  const loading = ref(false)

  async function fetchCases(search?: string) {
    loading.value = true
    try {
      const resp = await listCases({ search })
      cases.value = resp.cases
      total.value = resp.total
    } finally {
      loading.value = false
    }
  }

  async function fetchCase(id: string) {
    loading.value = true
    try {
      currentCase.value = await getCaseApi(id)
    } finally {
      loading.value = false
    }
  }

  return { cases, currentCase, total, loading, fetchCases, fetchCase }
})
