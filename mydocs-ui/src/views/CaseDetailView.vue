<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'

const router = useRouter()
const toast = useToast()

onMounted(() => {
  toast.info('Cases feature is coming soon')
  router.push('/cases')
})
</script>

<template>
  <div />
</template>
