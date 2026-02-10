import { ref, onMounted, onUnmounted } from 'vue'

export function useResponsive() {
  const isMobile = ref(false)  // < 768px
  const isTablet = ref(false)  // 768-1023px
  const isDesktop = ref(false) // >= 1024px

  let mqMobile: MediaQueryList
  let mqDesktop: MediaQueryList

  function update() {
    if (typeof window === 'undefined') return
    const w = window.innerWidth
    isMobile.value = w < 768
    isTablet.value = w >= 768 && w < 1024
    isDesktop.value = w >= 1024
  }

  onMounted(() => {
    update()
    mqMobile = window.matchMedia('(max-width: 767px)')
    mqDesktop = window.matchMedia('(min-width: 1024px)')
    mqMobile.addEventListener('change', update)
    mqDesktop.addEventListener('change', update)
  })

  onUnmounted(() => {
    mqMobile?.removeEventListener('change', update)
    mqDesktop?.removeEventListener('change', update)
  })

  return { isMobile, isTablet, isDesktop }
}
