import { useState } from 'react'
import { Dock } from './components/Dock'
import { ErrorBoundary } from './components/ErrorBoundary'
import { UploadDialog } from './components/upload'
import { ActivityProvider } from './lib/activity'
import { matchRoute, useLocation } from './lib/router'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Dataset from './pages/Dataset'
import Datasets from './pages/Datasets'
import Landing from './pages/Landing'
import NotFound from './pages/NotFound'

const PAGES = { landing: Landing, datasets: Datasets, dataset: Dataset, chat: Chat, analytics: Analytics, notFound: NotFound }

export default function App() {
  const location = useLocation()
  const route = matchRoute(location.pathname)
  const [uploadOpen, setUploadOpen] = useState(false)
  const Page = PAGES[route.name]
  return (
    <ActivityProvider>
      <div className="min-h-screen pb-32">
        <ErrorBoundary key={location.pathname}>
          <Page params={route.params} search={location.search} onUpload={() => setUploadOpen(true)} />
        </ErrorBoundary>
      </div>
      <Dock route={route.name} onUpload={() => setUploadOpen(true)} />
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </ActivityProvider>
  )
}
