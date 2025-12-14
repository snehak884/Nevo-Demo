import { useAtom } from 'jotai';
import {distortionAtom} from '../store/atoms';

export const useDistortion = () => {
    const [distortion, setDistortion] = useAtom(distortionAtom);
    return { distortion, setDistortion };
};
