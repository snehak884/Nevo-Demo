import {useEffect, useState} from 'react';
import {ArrowRightIcon} from "@heroicons/react/24/solid";
import {Canvas} from "@react-three/fiber";
import DarkMatter from "./components/ai/DarkMatter.tsx";
import BouncingDots from "./components/ai/BouncingDots.tsx";
import VoiceInteraction from "./components/ai/VoiceInteraction.tsx";
import CarShowroom from "./components/showroom/CarShowroom.tsx";
import {useReasoning} from "./hooks/useReasoning.ts";
import {useSideBar} from "./hooks/useSideBar.ts";
import {useAtom} from "jotai/index";
import {receivedMessageAtom} from "./store/atoms.ts";

const AIShowroom = () => {
    const { reasoning } = useReasoning();
    const { showSidebar, setShowSidebar } = useSideBar();
    const [contentVisible, setContentVisible] = useState(false); // Content visibility for fade-in effect
    const [receivedMessage, setReceivedMessage] = useAtom(receivedMessageAtom);

    // useEffect(() => {
    //     // Connect to the WebSocket
    //     const socket = new WebSocket(WEBSOCKET_URL);

    //     // Handle WebSocket message event
    //     socket.onmessage = (event) => {
    //         if(event.data) {
    //             setReceivedMessage(event.data);  // Update state when data is received
    //         }
    //     };

    //     return () => {
    //         socket.close();  // Clean up the WebSocket connection
    //     };
    // }, []);

    // useEffect(() => {
    //     const session_id = localStorage.getItem('session_id');
    //     const socket = new WebSocket(`${WEBSOCKET_URL}/audio/${session_id}`);
    //     socket.binaryType = 'arraybuffer';

    //     socket.onmessage = (event) => {
    //         if (event.data instanceof ArrayBuffer) {
    //             const uint8Array = new Uint8Array(event.data);
    //             queueAudio(uint8Array);
    //         } else {
    //             try {
    //                 const jsonData = JSON.parse(event.data);
    //                 if (jsonData.type === 'END_OF_STREAM') {
    //                     console.log('End of stream received');
    //                     onStreamEnd?.();
    //                 }
    //             } catch (error) {
    //                 console.warn('Received non-binary message:', event.data);
    //                 console.error('Received error:', error);
    //             }
    //         }
    //     };
    
    //     socket.onclose = () => {
    //         console.log('WebSocket connection closed');
    //         onStreamEnd?.();
    //     };
    
    //     socket.onerror = (error) => {
    //         console.error('WebSocket error:', error);
    //         onStreamEnd?.();
    //     };
    
    //     // Return a function to close the WebSocket connection
    //     return () => {
    //         if (socket.readyState === WebSocket.OPEN) {
    //             socket.close();
    //         }
    //     };
    
    // }, []);



    useEffect(() => {
        if(receivedMessage) {
            console.log('Received Message:', receivedMessage);
            setShowSidebar(true);
        }
    }, [receivedMessage, setShowSidebar]);

    // Control when to show content after sidebar animation
    useEffect(() => {
        if (showSidebar) {
            // Delay content fade-in to match sidebar transition
            const timer = setTimeout(() => setContentVisible(true), 300); // Adjust delay to match sidebar transition duration
            return () => clearTimeout(timer);
        } else {
            setContentVisible(false); // Immediately hide content when sidebar closes
        }
    }, [showSidebar]);

    return (
        <div className="w-full h-screen bg-[#b1abab] flex relative transition-all duration-500">

            {/* Stylish Button to Open/Close Sidebar */}
            <div
                className="absolute top-5 right-5 cursor-pointer z-10"
                onClick={() => setShowSidebar(!showSidebar)}
            >
                {/* Rotate arrow based on sidebar state */}
                <div
                    className={`transform transition-transform duration-500 ${showSidebar ? 'rotate-0' : 'rotate-180'}`}>
                    <ArrowRightIcon className="h-6 w-6 text-white"/>
                </div>

            </div>

            <div
                className={`transition-transform duration-500 h-full w-full flex flex-col justify-center items-center ${showSidebar ? 'translate-x-[-25%]' : ''}`}>
                <Canvas className={'transition-transform duration-500'} shadows dpr={[1, 2]}
                        camera={{position: [-5, 0, 4], fov: 25}}>
                    <DarkMatter/>
                    <BouncingDots show={reasoning}/>
                    {/*<FrequencyBars volume={volume} data={data} />*/}
                </Canvas>
                <VoiceInteraction/>
            </div>

            {showSidebar && (
                <div
                    className="absolute right-0 w-2/4 h-full bg-transparent p-4 transition-transform duration-500 flex justify-center items-center overflow-hidden">
                    <div
                        className={`transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'} delay-300`}>
                        <CarShowroom/>
                    </div>
                    {/* Floating border */}
                    <div className="border-drawing"/>
                </div>
            )}

        </div>
    );
};

export default AIShowroom;
