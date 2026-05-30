const isDesktop = window.matchMedia('(min-width: 768px)').matches

if (isDesktop) {
  void import('./main.tsx')
} else {
  window.location.replace('/eink')
}
