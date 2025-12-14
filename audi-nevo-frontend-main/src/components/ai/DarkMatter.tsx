import {Suspense, useRef} from 'react';
import {ContactShadows, Environment, MeshDistortMaterial, PerspectiveCamera} from "@react-three/drei";
import {useFrame} from "@react-three/fiber";
import * as THREE from 'three';
import {a, useSpring} from '@react-spring/three';
//import {easing} from "maath";
import {MeshStandardMaterial} from "three";
import {useDistortion} from "../../hooks/useDistortion.ts";
import {useReasoning} from "../../hooks/useReasoning.ts";

const AnimatedMaterial = a(MeshDistortMaterial)

const DarkMatter = () => {
    const { distortion } = useDistortion();
    const { reasoning } = useReasoning();
    //const { showSidebar } = useSideBar();
    const sphere = useRef<THREE.Mesh>(null);
    const light = useRef<THREE.PointLight>(null);
    // Smooth transition for distortion using react-spring
    const { smoothedDistortion } = useSpring({
        smoothedDistortion: distortion === 0 ? 0 : Math.log(distortion + 1) / Math.log(201),
        config: { mass: 1, tension: 120, friction: 14 }, // Adjust for smoothness
    });


    useFrame((state) => {

        if (sphere.current) {
            // Make the bubble float
            sphere.current.position.y = .1 + Math.sin(state.clock.elapsedTime / 1.5) / 12
        }

        // //Move camera according to mouse position
        // easing.damp3(
        //     state.camera.position,
        //     [Math.sin(-state.pointer.x) * 5, state.pointer.y * .5, 15 + Math.cos(state.pointer.x) * 2],
        //     0.2,
        //     delta,
        // );
        state.camera.lookAt(0, 0, 0);


        if (reasoning && sphere.current) {
            // Adjust emissive color and intensity over time to create a glowing effect
            const time = state.clock.getElapsedTime();
            const glowIntensity = (Math.sin(time * 1.2) + 1) / 4; // Sin wave to oscillate between 0 and 1
            if(sphere.current.material instanceof MeshStandardMaterial) {
                sphere.current.material.emissive.setHSL(0, 0, glowIntensity * 0.1); // Vary the lightness
                sphere.current.material.emissiveIntensity = glowIntensity;
            }
            // const material = sphere.current.material as THREE.MeshStandardMaterial & {
            //     distort: number;
            //     emissiveIntensity: number;
            // };
            //material.distort = 0.3 + Math.sin(time) * 0.1;
        }
    });

    return (
        <>
            <PerspectiveCamera makeDefault position={[0, 0, 10]} fov={20}>
                <ambientLight intensity={0.5}/>
                <pointLight ref={light} position-z={0} intensity={.1} color="#F8C069"/>
            </PerspectiveCamera>
            <Suspense fallback={null}>
                <a.mesh ref={sphere} scale={.6} castShadow position={[0, 30, 0]}>
                    <sphereGeometry args={[1, 64, 64]}/>
                    <AnimatedMaterial
                        distort={smoothedDistortion.to(value => value * 0.6)} // Use the distortion value passed from props
                        speed={1.5}
                        color={'#202020'}
                        envMapIntensity={1}
                        clearcoat={1}
                        clearcoatRoughness={0}
                        metalness={0.1}
                        emissive={'#202020'}
                        emissiveIntensity={0.5}
                    />
                </a.mesh>
                <Environment files="/hdri/dikhololo_night_1k.hdr"/>
                <ContactShadows
                    rotation={[Math.PI / 2, 0, 0]}
                    position={[0, -1.3, 0]}
                    opacity={1}
                    width={5}
                    height={5}
                    blur={1}
                    far={2}
                />
            </Suspense>
        </>

    );
};

export default DarkMatter;
