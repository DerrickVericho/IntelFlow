import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { createQueryClient } from '../api/query'
import { App } from './App'
import './theme.css'

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={createQueryClient()}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>,
)
