import {useRef, useState} from 'react';
import * as THREE from 'three';
import {Vector3} from "@react-three/fiber";
import {useSpring, animated, config} from "@react-spring/three";


interface ISphere {
    id: number;
    color: string;
    position: Vector3 | undefined;
    scale?: number;
    selected?: number | null;
    onSelect?: () => void;
}

const Sphere = ({ id, color = '#202020', position, selected, onSelect }: ISphere) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);
    const {scale} = useSpring({
        scale: selected === id ? 1.4 : hovered && selected !== id ? 1.1 : 1,
        config: config.wobbly,
    });


    return (
        <animated.mesh
            onPointerOver={() => setHovered(true)}
            onPointerOut={() => setHovered(false)}
            ref={meshRef}
            position={position}
            scale={scale}
            onClick={onSelect}
        >
            <sphereGeometry args={[1, 64, 64]}/>
            <meshStandardMaterial color={color} metalness={.7} roughness={0.3} />
        </animated.mesh>
    );
};

export default Sphere;
