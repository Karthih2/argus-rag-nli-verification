import { useEffect } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Navbar } from './components/Navbar'
import { ActivityProvider } from './lib/activity'
import { matchRoute, navigate, useLocation } from './lib/router'
import Analytics from './pages/Analytics'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Landing from './pages/Landing'
import NotFound from './pages/NotFound'
import Processing from './pages/Processing'
import Upload from './pages/Upload'

const PAGES = { landing: Landing, upload: Upload, processing: Processing, dashboard: Dashboard, history: History, analytics: Analytics, notFound: NotFound }

export default function App() {
  const location = useLocation()
  const route = matchRoute(location.pathname)
  const Page = PAGES[route.name]

  // On page reload/refresh, persist to MongoDB has already occurred, and throw the user out to History
  useEffect(() => {
    try {
      const navEntries = performance.getEntriesByType('navigation')
      const isReload = (navEntries.length > 0 && navEntries[0].type === 'reload') || performance.navigation?.type === 1
      if (isReload && (window.location.pathname.startsWith('/dashboard') || window.location.pathname.startsWith('/processing'))) {
        navigate('/history', { replace: true })
      }
    } catch (e) {
      console.warn('Navigation check failed', e)
    }
  }, [])

  return (
    <ActivityProvider>
      <Navbar route={route.name} onUpload={() => navigate('/upload')} />
      <div className="min-h-[calc(100vh-57px)]">
        <ErrorBoundary key={location.pathname}>
          <Page params={route.params} search={location.search} />
        </ErrorBoundary>
      </div>
    </ActivityProvider>
  )
}
