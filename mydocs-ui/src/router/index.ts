import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuth } from '@/auth/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'gallery',
      component: () => import('@/views/GalleryView.vue'),
      meta: { tab: 'documents' },
    },
    {
      path: '/doc/:id',
      name: 'doc-viewer',
      component: () => import('@/views/GalleryView.vue'),
      meta: { tab: 'documents' },
    },
    {
      path: '/cases',
      name: 'cases',
      component: () => import('@/views/CasesGalleryView.vue'),
      meta: { tab: 'cases' },
    },
    {
      path: '/cases/:id',
      name: 'case-detail',
      component: () => import('@/views/CaseDetailView.vue'),
      meta: { tab: 'cases' },
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/GalleryView.vue'),
      meta: { tab: 'documents', modal: 'upload' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/GalleryView.vue'),
      meta: { tab: 'documents', modal: 'settings' },
    },

    // Legacy redirects
    { path: '/documents', redirect: '/' },
    { path: '/documents/:id', redirect: (to) => `/doc/${to.params.id}` },
    { path: '/documents/:id/view', redirect: (to) => `/doc/${to.params.id}` },
    { path: '/search', redirect: (to) => ({ path: '/', query: to.query }) },
  ],
})

router.beforeEach((to, _from) => {
  // Auth guard: redirect unauthenticated users to /login
  const { isAuthenticated } = useAuth()
  if (!to.meta.public && !isAuthenticated.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && isAuthenticated.value) {
    return { path: '/' }
  }

  // Sync activeTab from route meta
  const appStore = useAppStore()
  const tab = to.meta.tab as 'documents' | 'cases' | undefined
  if (tab) {
    appStore.activeTab = tab
  }

  // Open viewer from /doc/:id params
  if (to.name === 'doc-viewer' && to.params.id) {
    const page = Number(to.query.page) || 1
    const highlight = decodeURIComponent((to.query.highlight as string) || '')
    appStore.openViewer(to.params.id as string, page, highlight)
  } else if (to.name !== 'doc-viewer') {
    // Close viewer when navigating away from doc routes
    if (appStore.viewerOpen && !to.path.startsWith('/doc/')) {
      appStore.closeViewer()
    }
  }
})

export default router
