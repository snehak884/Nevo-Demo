import { atom } from 'jotai';


export const distortionAtom = atom<number>(0);

export const isRecordingAtom = atom<boolean>(false);

export const reasoningAtom = atom<boolean>(false);

export const showSidebarAtom = atom<boolean>(false);

export const receivedMessageAtom = atom<string>('');
