export const WEBSOCKET_URL = 
  import.meta.env.VITE_ENVIRONMENT === "local"
    ? "ws://localhost:8000/ws"
    : import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8000/ws";

export const API_URL = 
  import.meta.env.VITE_ENVIRONMENT === "local"
    ? "http://localhost:8000"
    : import.meta.env.VITE_BACKEND_URL;