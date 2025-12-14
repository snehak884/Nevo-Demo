import { useAtom } from 'jotai';
import {useEffect, useRef, useState} from 'react';
import { isRecordingAtom } from '../store/atoms';

export const useAudioVisualizer = () => {
    const [volume, setVolume] = useState(0);
    const [data, setData] = useState<Uint8Array>(new Uint8Array(0));
    const [ isRecording ] = useAtom(isRecordingAtom);
    useEffect(() => {
        const initAudio = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const audioContext = new window.AudioContext();
                const analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);

                const source = audioContext.createMediaStreamSource(stream);
                source.connect(analyser);

                const getAverageVolume = (array: Uint8Array) => {
                    let values = 0;
                    for (let i = 0; i < array.length; i++) {
                        values += array[i];
                    }
                    return values / array.length;
                };

                const visualize = (analyser: AnalyserNode, dataArray: Uint8Array, setVolume: (volume: number) => void) => {
                    analyser.getByteFrequencyData(dataArray);
                    setData(dataArray);
                    const avgVolume = getAverageVolume(dataArray);
                    setVolume(avgVolume); // Update state to re-render component
                    if (isRecording) {
                        animationFrameId.current = requestAnimationFrame(() => visualize(analyser, dataArray, setVolume));
                    }
                };

                if (isRecording) {
                    visualize(analyser, dataArray, setVolume);
                }

            } catch (error) {
                console.error('Microphone access denied or error:', error);
            }
        };
        initAudio();
    }, [isRecording]);


    const animationFrameId = useRef<number | null>(null);

    useEffect(() => {
        if (!isRecording && animationFrameId.current !== null) {
            cancelAnimationFrame(animationFrameId.current);
            setData(new Uint8Array(32));
        }
    }, [isRecording]);


    return { volume, data };
};
