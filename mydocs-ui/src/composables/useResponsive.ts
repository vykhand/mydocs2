import { ref, onMounted, onUnmounted } from 'vue'

export function useResponsive() {
  const isMobile = ref(false)  // < 768px
  const isTablet = ref(false)  // 768-1023px
  const isDesktop = ref(false) // 1024-1279px
  const isWide = ref(false)    // >= 1280px

  let mqMobile: MediaQueryList
  let mqDesktop: MediaQueryList
  let mqWide: MediaQueryList

  function update() {
    if (typeof window === 'undefined') return
    const w = window.innerWidth
    isMobile.value = w < 768
    isTablet.value = w >= 768 && w < 1024
    isDesktop.value = w >= 1024 && w < 1280
    isWide.value = w >= 1280
  }

  onMounted(() => {
    update()
    mqMobile = window.matchMedia('(max-width: 767px)')
    mqDesktop = window.matchMedia('(min-width: 1024px)')
    mqWide = window.matchMedia('(min-width: 1280px)')
    mqMobile.addEventListener('change', update)
    mqDesktop.addEventListener('change', update)
    mqWide.addEventListener('change', update)
  })

  onUnmounted(() => {
    mqMobile?.removeEventListener('change', update)
    mqDesktop?.removeEventListener('change', update)
    mqWide?.removeEventListener('change', update)
  })

  return { isMobile, isTablet, isDesktop, isWide }
}
