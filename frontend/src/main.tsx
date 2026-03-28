import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

// Initialize theme from localStorage
const savedTheme = localStorage.getItem('prophet-theme') || 'dark';
if (savedTheme === 'light') {
  document.documentElement.classList.add('light');
  document.documentElement.setAttribute('data-theme', 'light');
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
