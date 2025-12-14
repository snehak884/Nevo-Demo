import { useAtom } from 'jotai';
import {reasoningAtom} from '../store/atoms';

export const useReasoning = () => {
    const [reasoning, setReasoning] = useAtom(reasoningAtom);
    return { reasoning, setReasoning };
}
