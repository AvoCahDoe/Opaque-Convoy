import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import DocPage from './pages/DocPage'
import TryPage from './pages/TryPage'
import ResultsPage from './pages/ResultsPage'
import { ConvoyProvider } from './state/ConvoyContext'

export default function App() {
  return (
    <BrowserRouter>
      <ConvoyProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/try" replace />} />
            <Route path="doc" element={<DocPage />} />
            <Route path="try" element={<TryPage />} />
            <Route path="results" element={<ResultsPage />} />
            <Route path="*" element={<Navigate to="/try" replace />} />
          </Route>
        </Routes>
      </ConvoyProvider>
    </BrowserRouter>
  )
}
