import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Commented out StrictMode to avoid error with WebSockets. WebSockets doesn't work with StrictMode.
createRoot(document.getElementById('root')!).render(
  //<StrictMode>
    <App />
  //</StrictMode>,
)
