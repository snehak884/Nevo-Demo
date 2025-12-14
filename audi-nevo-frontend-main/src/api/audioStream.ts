import axios from "axios";
import { WEBSOCKET_URL, API_URL } from '../constants/constants.ts';

export const sendAudioBlob = async (blob: Blob) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    formData.append("file", blob);

    try {
        return await axios.post(`${API_URL}/receive_audio_blob`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                Authorization: `Bearer ${token}`,
            },
        });

    } catch (error) {
        console.error('Error sending audio blob: ', error);
    }
}

export const getAudioStream = (
    queueAudio: (pcmData: Uint8Array) => void,
    onStreamEnd?: () => void
) => {
    const socket = new WebSocket(`${WEBSOCKET_URL}/audio`);

    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
        console.log('WebSocket connection established');
        // Send a message to start the audio stream
        socket.send('start');
    };

    socket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            const uint8Array = new Uint8Array(event.data);
            queueAudio(uint8Array);
        } else {
            try {
                const jsonData = JSON.parse(event.data);
                if (jsonData.type === 'END_OF_STREAM') {
                    console.log('End of stream received');
                    onStreamEnd?.();
                }
            } catch (error) {
                console.warn('Received non-binary message:', event.data);
                console.error('Received error:', error);
            }
        }
    };

    socket.onclose = () => {
        console.log('WebSocket connection closed');
        onStreamEnd?.();
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        onStreamEnd?.();
    };

    // Return a function to close the WebSocket connection
    return () => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
    };
};


