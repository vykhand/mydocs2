import { ref } from 'vue'
import { search as apiSearch } from '@/api/search'
import type { SearchRequest, SearchResponse } from '@/types'

export function useSearch() {
  const query = ref('')
  const config = ref<SearchRequest>({
    query: '',
    search_target: 'pages',
    search_mode: 'hybrid',
    top_k: 10,
    min_score: 0,
  })
  const results = ref<SearchResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute() {
    if (!query.value.trim()) return
    loading.value = true
    error.value = null
    try {
      config.value.query = query.value
      results.value = await apiSearch(config.value)
    } catch (e: any) {
      error.value = e.message || 'Search failed'
    } finally {
      loading.value = false
    }
  }

  function reset() {
    query.value = ''
    results.value = null
    error.value = null
  }

  return { query, config, results, loading, error, execute, reset }
}
