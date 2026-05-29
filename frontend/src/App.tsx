import { Dashboard } from '@/components/Dashboard'
import { ItemsPage } from '@/components/ItemsPage'
import { StreamsPage } from '@/components/StreamsPage'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

type View = 'dashboard' | 'items' | 'streams'

function AppContent() {
  const [view, setView] = useState<View>('dashboard')

  if (view === 'items') {
    return <ItemsPage onBack={() => setView('dashboard')} />
  }

  if (view === 'streams') {
    return <StreamsPage onBack={() => setView('dashboard')} />
  }

  return (
    <Dashboard
      onViewItems={() => setView('items')}
      onViewStreams={() => setView('streams')}
    />
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App
