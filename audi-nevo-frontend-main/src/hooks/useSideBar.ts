import {useAtom} from "jotai";
import {showSidebarAtom} from "../store/atoms.ts";

export const useSideBar = () => {
    const [showSidebar, setShowSidebar] = useAtom(showSidebarAtom);
    return {showSidebar , setShowSidebar};
};
