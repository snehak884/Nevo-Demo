import { useEffect } from 'react';
import { API_URL } from '../constants/constants.ts';

function usePageReload() {
    const endpointUrl = `${API_URL}/create_chatbot`;

    useEffect(() => {
        // Set a flag in sessionStorage before the page unloads
        const handleBeforeUnload = () => {
            sessionStorage.setItem('reloaded', 'true');
        };
        window.addEventListener('beforeunload', handleBeforeUnload);

        // Check on page load if it was a reload and call the endpoint if needed
        const handleReloadCheck = async () => {
            if (sessionStorage.getItem('reloaded')) {
                // Clear the reload flag
                sessionStorage.removeItem('reloaded');

                try {
                    // Make the API call
                    const response = await fetch(endpointUrl);
                    console.log('Endpoint called on reload:', response);
                } catch (error) {
                    console.error('Error calling endpoint:', error);
                }
            }
        };

        // Run the reload check when component mounts
        handleReloadCheck();

        // Clean up the beforeunload listener on unmount
        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [endpointUrl]);
}

export default usePageReload;
