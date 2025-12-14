import { useEffect, useRef, useState } from "react";
import { ReactMic, ReactMicStopEvent } from "react-mic";
import { sendAudioBlob } from "../../api/audioStream.ts";
import MicIcon from "./MicIcon.tsx";
import { useReasoning } from "../../hooks/useReasoning.ts";
import { isRecordingAtom } from "../../store/atoms.ts";
import { useAtom } from "jotai";
import { useDistortion } from "../../hooks/useDistortion.ts";
import { getAverageVolume } from "../../helpers/audio.ts";
import { WEBSOCKET_URL } from "../../constants/constants.ts";
// import { and, assign } from "three/examples/jsm/nodes/Nodes.js";
// import { setUpdateRange } from "@react-three/drei/helpers/deprecated";
import {receivedMessageAtom} from "../../store/atoms.ts";

const VoiceInteraction = () => {
    const { setDistortion } = useDistortion();
    const { reasoning, setReasoning } = useReasoning();
    const [isRecording, setIsRecording] = useAtom(isRecordingAtom);
    const [receivedMessage, setReceivedMessage] = useAtom(receivedMessageAtom);


    // const [insideAudio, setInsideAudio] = useState(false);

    const [aiStatusMessage, setAiStatusMessage] = useState('Press the space bar to speak!');

    const analyserNodeRef = useRef<AnalyserNode | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    // const [audioBufferQueue, setAudioBufferQueue] = useState<AudioBuffer[]>([]);
    // const isPlayingRef = useRef(false);
    const audioStartTimeRef = useRef(0);
    const allowRecordingRef = useRef(true);
    // const isStreamingRef = useRef(true);

    const numSourcesPlaying = useRef(0);


    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.code === 'Space' && allowRecordingRef.current) {
                setIsRecording(true);
                setAiStatusMessage('Recording...');
            }
        };

        const handleKeyUp = (event: KeyboardEvent) => {
            if (event.code === 'Space' && isRecording && allowRecordingRef.current) {
                allowRecordingRef.current = false;
                setIsRecording(false);
                setAiStatusMessage('AI is thinking...');
                setReasoning(true); // start bounding dots animation
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, [isRecording]);


    useEffect(() => {
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
                sampleRate: 24000, // Match PCM data sample rate
            });
        }
    }, []);

    useEffect(() => {
        if (!audioContextRef.current) return;

        // Global AnalyserNode to stay connected throughout playback
        if (!analyserNodeRef.current) {
            analyserNodeRef.current = audioContextRef.current.createAnalyser();
            analyserNodeRef.current.fftSize = 256;
        }
        const analyserNode = analyserNodeRef.current;
        const frequencyDataArray = new Uint8Array(analyserNode.frequencyBinCount);
        const updateAnimation = () => {
            analyserNode.getByteFrequencyData(frequencyDataArray);

            // Update DOM or canvas with frequency data for the animation
            if (frequencyDataArray.some(value => value > 0)) {
                const average = getAverageVolume(frequencyDataArray); // Use this data for volume
                setDistortion(2 * average);
            } else {
                setDistortion(0);
            }
            requestAnimationFrame(updateAnimation);

        };
        requestAnimationFrame(updateAnimation);
    }, []);

    const queueAudioChunk = (pcmData: Uint8Array) => {
        if (!audioContextRef.current) return;
        if (pcmData.length === 0) return;

        const sampleRate = 24000; // Match the sample rate of your PCM data
        const numChannels = 1;
        const bytesPerSample = 2; // 16-bit PCM data

        const totalSamples = pcmData.length / bytesPerSample;
        const audioBuffer = audioContextRef.current.createBuffer(
            numChannels,
            totalSamples,
            sampleRate
        );

        const channelData = audioBuffer.getChannelData(0);

        for (let i = 0; i < totalSamples; i++) {
            const index = i * bytesPerSample;
            // Read 16-bit signed integer (little-endian)
            // Convert from 16-bit signed integer to float (-1 to 1)
            let intSample = pcmData[index] | (pcmData[index + 1] << 8);
            if (intSample >= 0x8000) {
                intSample = intSample - 0x10000;
            }
            channelData[i] = intSample / 32768;
        }
        const source = audioContextRef.current.createBufferSource();
        source.buffer = audioBuffer;

        // Global AnalyserNode to stay connected throughout playback
        if (!analyserNodeRef.current) {
            analyserNodeRef.current = audioContextRef.current.createAnalyser();
            analyserNodeRef.current.fftSize = 256;
        }
        const analyserNode = analyserNodeRef.current;
        // Connect source to global AnalyserNode
        source.connect(analyserNode);
        analyserNode.connect(audioContextRef.current.destination);

        if (audioStartTimeRef.current < audioContextRef.current.currentTime) {
            audioStartTimeRef.current = audioContextRef.current.currentTime;
        }

        source.start(audioStartTimeRef.current);
        audioStartTimeRef.current += audioBuffer.duration;
        numSourcesPlaying.current += 1;
        setAiStatusMessage('AI is speaking...');
        setReasoning(false); // stop bounding dots animation

        source.onended = () => {
            numSourcesPlaying.current -= 1;
            console.log('Audio source ended, remaining sources playing:', numSourcesPlaying.current);
            if (numSourcesPlaying.current === 0) {
                console.log('Played all the audio buffer, based numSourcesPlaying');
                allowRecordingRef.current = true;
                setAiStatusMessage('Press the space bar to speak!');
            }
        };

    };

    const onStreamEnd = () => {
        console.log('Stream ended');
    };

    const onStop = async (recordedBlob: ReactMicStopEvent) => {
        await sendAudio(recordedBlob.blob);
        setIsRecording(false);
    };

    const sendAudio = async (recordedBlob: Blob) => {
        console.log('Sending audio blob...');
        await sendAudioBlob(recordedBlob);
    };

    useEffect(() => {
        const session_id = localStorage.getItem('session_id');
        console.log('Session ID:', session_id, 'Websocket URL:', `${WEBSOCKET_URL}/audio/${session_id}`);
        const socket = new WebSocket(`${WEBSOCKET_URL}/audio/${session_id}`);
        socket.binaryType = 'arraybuffer';

        socket.onmessage = (event) => {
            if (event.data instanceof ArrayBuffer) {
                const uint8Array = new Uint8Array(event.data);
                queueAudioChunk(uint8Array);
            } else {
                try {
                    const jsonObj = JSON.parse(event.data);
                    if (jsonObj.type === 'END_OF_STREAM') {
                        console.log('End of stream received');
                        onStreamEnd?.();
                    }
                    else if (jsonObj.type === 'show_image') {
                        console.log('Websocket got message:', jsonObj.type);
                        setReceivedMessage(event.data);
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

    }, []);


    return (
        <div className={'transform -translate-x-[-25%]flex flex-col justify-center items-center m-auto mb-20'}>
            <ReactMic
                record={isRecording}
                className={'sound-wave max-w-44'}
                onStop={onStop}
                visualSetting={'frequencyBars'}
                strokeColor="#ffffff"
                backgroundColor="#b1abab"
            />

            <div className={'flex flex-col items-center'}>
                <MicIcon className={"m-2 text-white"} />

                <h3 className={'text-white font-bold mt-4'}>
                    {aiStatusMessage}
                </h3>
            </div>

        </div>
    );
};

export default VoiceInteraction;
