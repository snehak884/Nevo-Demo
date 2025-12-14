import './App.css'
// import usePageReload from "./hooks/usePageReload.ts";
import AIShowroom from "./AIShowroom.tsx";
import {useState} from "react";
import Login from "./Login.tsx";

function App() {
    // usePageReload(); // Handle clean up when the page reloads
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    return (
        <main className="w-full h-screen flex relative">
            {isAuthenticated ? <AIShowroom/> : <Login onAuthenticated={setIsAuthenticated}/> }
        </main>

    )
}

export default App
