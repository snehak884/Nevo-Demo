import {SetStateAction, useState} from 'react';
import {API_URL} from "./constants/constants.ts";
import Spinner from "./components/Spinner.tsx";
import axios from "axios";

const Login = ({onAuthenticated}: { onAuthenticated: (isAuthenticated: boolean) => void }) => {
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e: { target: { value: SetStateAction<string>; }; }) => {
        setPassword(e.target.value);
    };

    const handleLogin = async (password: string) => {
        setLoading(true);
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password }),
            credentials: "include"  // Include credentials to allow cookies
        });
        const data = await response.json();
        setLoading(false)
        if (response.ok) {
            localStorage.setItem("token", data.token);
            localStorage.setItem("session_id", data.session_id);

            axios.defaults.withCredentials = true
            document.cookie = `session_id=${data.session_id}; token=${data.token}`;

            onAuthenticated(true);
        } else {
            alert("Invalid password");
        }
    };

    const handleSubmit = (e: { preventDefault: () => void; }) => {
        e.preventDefault();
        handleLogin(password);
        setPassword(''); // Clear the input after submission
    };
    return (
        <div className="flex items-center justify-center h-screen w-full bg-[#202020] text-gray-200">


            {loading ? <Spinner /> :
                <form onSubmit={handleSubmit} className="flex items-center space-x-4">
                <input
                    type="password"
                    value={password}
                    onChange={handleChange}
                    placeholder="Enter Password"
                    autoComplete={'current-password'}
                    className="px-4 py-2 bg-[#101010] text-white rounded-md focus:outline-none focus:ring-2 focus:ring-[#b1abab]"
                />
                <button
                    type="submit"
                    className="px-6 py-2 text-white bg-[#b1abab] rounded-r-md hover:text-black hover:bg-white focus:outline-none focus:ring-[#b1abab] focus:border-[#b1abab]"
                    disabled={loading}
                >
                    Login
                </button>
            </form>}
        </div>
    );
};

export default Login;
