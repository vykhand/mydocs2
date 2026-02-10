import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { SearchRequest, SearchResponse, SearchMode, SearchTarget } from '@/types'
import { search as apiSearch } from '@/api/search'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const searchTarget = ref<SearchTarget>('pages')
  const searchMode = ref<SearchMode>('hybrid')
  const loading = ref(false)
  const response = ref<SearchResponse | null>(null)

  const config = reactive<Partial<SearchRequest>>({
    top_k: 10,
    min_score: 0.0,
  })

  async function executeSearch() {
    if (!query.value.trim()) return
    loading.value = true
    try {
      const request: SearchRequest = {
        query: query.value,
        search_target: searchTarget.value,
        search_mode: searchMode.value,
        top_k: config.top_k || 10,
        min_score: config.min_score || 0.0,
        ...config,
      }
      response.value = await apiSearch(request)
    } finally {
      loading.value = false
    }
  }

  function reset() {
    query.value = ''
    response.value = null
    searchMode.value = 'hybrid'
    searchTarget.value = 'pages'
  }

  return { query, searchTarget, searchMode, loading, response, config, executeSearch, reset }
})
