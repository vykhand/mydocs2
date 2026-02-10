import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/documents',
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/UploadView.vue'),
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('@/views/DocumentsView.vue'),
    },
    {
      path: '/documents/:id',
      name: 'document-detail',
      component: () => import('@/views/DocumentDetailView.vue'),
    },
    {
      path: '/documents/:id/view',
      name: 'document-viewer',
      component: () => import('@/views/DocumentViewerView.vue'),
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
    },
    {
      path: '/cases',
      name: 'cases',
      component: () => import('@/views/CasesView.vue'),
    },
    {
      path: '/cases/:id',
      name: 'case-detail',
      component: () => import('@/views/CaseDetailView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

export default router
