import {useRef} from "react";
import {useFrame} from "@react-three/fiber";
import {InstancedMesh, Object3D} from "three";

//To be used in case of a 3D frequency bar visualization
export const FrequencyBars = ({ data }: { volume?: number, data: Uint8Array })=> {
    const obj = new Object3D();
    const ref = useRef<InstancedMesh>(null);
    useFrame(() => {
        if(ref.current){
            for (let i = 0; i < 32; i++) {
                obj.position.set(i * 0.04, data[i] / 1000, 0)
                obj.updateMatrix()
                ref.current.setMatrixAt(i, obj.matrix)
            }
            ref.current.instanceMatrix.needsUpdate = true
        }
    })
    return (
        <instancedMesh ref={ref} args={[undefined, undefined, 32]} position={[-.6,-1.6,0]}>
            <planeGeometry args={[0.02, 0.05]} />
            <meshBasicMaterial toneMapped={false} transparent opacity={1} />
        </instancedMesh>
    )
}
