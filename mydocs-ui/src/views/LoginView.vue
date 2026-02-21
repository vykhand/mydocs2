<script setup lang="ts">
import { useAuth } from '@/auth/useAuth'
import { LogIn } from 'lucide-vue-next'

const { login } = useAuth()
</script>

<template>
  <div
    class="flex items-center justify-center min-h-screen"
    style="background-color: var(--color-bg-primary);"
  >
    <div
      class="flex flex-col items-center gap-6 p-10 rounded-2xl border shadow-lg max-w-sm w-full"
      style="background-color: var(--color-bg-secondary); border-color: var(--color-border);"
    >
      <h1 class="text-2xl font-bold" style="color: var(--color-text-primary);">
        mydocs
      </h1>
      <p class="text-sm text-center" style="color: var(--color-text-secondary);">
        Sign in with your Microsoft account to continue.
      </p>
      <button
        @click="login"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white w-full justify-center"
        style="background-color: var(--color-accent);"
      >
        <LogIn :size="18" />
        Sign in with Microsoft
      </button>
    </div>
  </div>
</template>
