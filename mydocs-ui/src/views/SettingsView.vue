<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useSettingsStore } from '@/stores/settings'
import { checkHealth } from '@/api/health'

const appStore = useAppStore()
const settingsStore = useSettingsStore()

const isAdvanced = computed(() => appStore.mode === 'advanced')

const health = ref<{ status: string; latencyMs: number }>({ status: 'checking', latencyMs: 0 })

onMounted(async () => {
  health.value = await checkHealth()
})

async function refreshHealth() {
  health.value = { status: 'checking', latencyMs: 0 }
  health.value = await checkHealth()
}
</script>

<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <h1 class="text-2xl font-semibold" style="color: var(--color-text-primary);">Settings</h1>

    <!-- Theme -->
    <section
      class="rounded-lg border p-4"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Theme</h2>
      <div class="flex gap-2">
        <button
          v-for="t in (['light', 'dark', 'system'] as const)"
          :key="t"
          @click="appStore.setTheme(t)"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
          :style="{
            backgroundColor: appStore.theme === t ? 'var(--color-accent)' : 'var(--color-bg-tertiary)',
            color: appStore.theme === t ? '#fff' : 'var(--color-text-secondary)',
          }"
        >
          {{ t.charAt(0).toUpperCase() + t.slice(1) }}
        </button>
      </div>
    </section>

    <!-- Search Defaults -->
    <section
      class="rounded-lg border p-4 space-y-3"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <h2 class="text-sm font-semibold" style="color: var(--color-text-primary);">Search Defaults</h2>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Default Search Mode</label>
        <select
          v-model="settingsStore.defaultSearchMode"
          class="rounded-lg border px-3 py-2 text-sm w-full"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        >
          <option value="hybrid">Hybrid</option>
          <option value="fulltext">Fulltext</option>
          <option value="vector">Vector</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Default Top K</label>
        <input
          v-model.number="settingsStore.defaultTopK"
          type="number"
          min="1"
          max="100"
          class="rounded-lg border px-3 py-2 text-sm w-full"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        />
      </div>
    </section>

    <!-- Parser Defaults (Advanced only) -->
    <section
      v-if="isAdvanced"
      class="rounded-lg border p-4 space-y-3"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <h2 class="text-sm font-semibold" style="color: var(--color-text-primary);">Parser Defaults</h2>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Azure DI Model</label>
        <input
          v-model="settingsStore.defaultParserModel"
          class="rounded-lg border px-3 py-2 text-sm w-full"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        />
      </div>
      <div>
        <label class="block text-xs font-medium mb-1" style="color: var(--color-text-secondary);">Embedding Model</label>
        <input
          v-model="settingsStore.defaultEmbeddingModel"
          class="rounded-lg border px-3 py-2 text-sm w-full"
          style="background-color: var(--color-bg-primary); border-color: var(--color-border); color: var(--color-text-primary);"
        />
      </div>
    </section>

    <!-- Connection Info -->
    <section
      class="rounded-lg border p-4"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <h2 class="text-sm font-semibold mb-3" style="color: var(--color-text-primary);">Connection</h2>
      <div class="flex items-center gap-3">
        <div
          class="w-3 h-3 rounded-full"
          :style="{
            backgroundColor: health.status === 'ok' ? 'var(--color-success)' : health.status === 'checking' ? 'var(--color-warning)' : 'var(--color-danger)',
          }"
        />
        <div>
          <p class="text-sm" style="color: var(--color-text-primary);">
            Backend: {{ health.status === 'ok' ? 'Connected' : health.status === 'checking' ? 'Checking...' : 'Disconnected' }}
          </p>
          <p v-if="health.latencyMs" class="text-xs" style="color: var(--color-text-secondary);">
            Latency: {{ health.latencyMs }}ms
          </p>
        </div>
        <button
          @click="refreshHealth"
          class="ml-auto text-xs px-3 py-1.5 rounded-md border"
          style="border-color: var(--color-border); color: var(--color-text-secondary);"
        >
          Refresh
        </button>
      </div>
    </section>

    <!-- About -->
    <section
      class="rounded-lg border p-4"
      style="border-color: var(--color-border); background-color: var(--color-bg-secondary);"
    >
      <h2 class="text-sm font-semibold mb-2" style="color: var(--color-text-primary);">About</h2>
      <p class="text-sm" style="color: var(--color-text-secondary);">mydocs v1.0.0</p>
      <p class="text-xs mt-1" style="color: var(--color-text-secondary);">AI-powered document parsing and information extraction</p>
    </section>
  </div>
</template>
