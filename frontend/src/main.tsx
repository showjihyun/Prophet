import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { LS_KEY_THEME, QUERY_STALE_TIME_MS, QUERY_RETRY_COUNT } from "@/config/constants";

// Initialize theme from localStorage
const savedTheme = localStorage.getItem(LS_KEY_THEME) || 'dark';
if (savedTheme === 'light') {
  document.documentElement.classList.add('light');
  document.documentElement.setAttribute('data-theme', 'light');
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: QUERY_RETRY_COUNT, staleTime: QUERY_STALE_TIME_MS },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
