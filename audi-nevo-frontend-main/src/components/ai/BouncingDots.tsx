import {useRef} from 'react';
import * as THREE from "three";
import {useFrame} from "@react-three/fiber";
import { useSpring, animated } from '@react-spring/three';

const BouncingDots = ({ color = '#202020', show = true }: { color?: string, show: boolean} ) => {
    const dotRefs = [useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null)];

    // Spring animation for smooth transition
    const { opacity } = useSpring({
        opacity: show ? 1 : 0,
        config: { duration: 500 }, // Control the speed of the fade
    });

    useFrame(({ clock }) => {


        // Animate each dot with a phase offset to create a jumping effect
        dotRefs.forEach((ref, index) => {
            const time = clock.getElapsedTime();
            if (ref.current) {
                // Adding an offset based on the index to create a staggered animation
                // ref.current.position.y = -1.2 + Math.sin(time * 8 + index) * 0.1;
                ref.current.position.y = -1.2 + Math.sin(time*9 + index) * 0.05
                const cyclePosition = 2 - Math.floor(time*3 % 3);
                // console.log('cyclePosition', cyclePosition);
                if(ref.current.material instanceof THREE.MeshPhongMaterial) {
                    if (cyclePosition != index) {
                        ref.current.material.color.set('#202020'); // light
                    } else {
                        ref.current.material.color.set('#CCCCCC'); // dark
                    }
                }

            }
        });
    });


    return (
        <animated.group scale={opacity}>
            <ambientLight intensity={0.5}/>
            <pointLight position={[0, 0, 0]} intensity={1}/>
            {dotRefs.map((ref, index) => (
                <mesh
                    key={index}
                    ref={ref}
                    position={[.4 - (index / 3) , 0, -5]} // Set positions with spacing (-1, 0, 1)
                    scale={.3} // Scale the dots
                >
                    <sphereGeometry args={[.3, 64, 64]}/>
                    <meshPhongMaterial color={color}/>
                </mesh>
            ))}
        </animated.group>
    );

};

export default BouncingDots;
