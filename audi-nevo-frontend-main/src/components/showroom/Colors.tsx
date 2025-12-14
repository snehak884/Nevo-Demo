import {Canvas} from "@react-three/fiber";
import Sphere from "./Sphere.tsx";
import {Environment} from "@react-three/drei";

const Colors = ({ colors }: {  colors: string[] }) => {
    return (
        <div>
            <Canvas shadows camera={{ position: [0, 15, 10], fov: 20 }}>
                {/* Bright Ambient Light */}
                <ambientLight intensity={0.6} /> {/* Increase this intensity for 7more overall light */}

                {/* Strong Directional Light */}
                <directionalLight position={[5, 5, 5]} intensity={1.5} />

                {/* Add multiple point lights to create bright spots on the spheres */}
                <pointLight position={[-5, 5, 5]} intensity={1} color="blue" castShadow={true}/>
                <pointLight position={[0, 5, 5]} intensity={1} color="red" castShadow={true} />
                <pointLight position={[5, 5, 5]} intensity={1} color="yellow" castShadow={true} />


                {colors && colors.map((color: string, index: number) => (
                        <Sphere key={index}
                                id={index}
                                color={color}
                                position={[-8 + index * 3, 0, 0]}
                        />
                    )
                )
                }
                <Environment preset="city" />
            </Canvas>
        </div>
    );
};

export default Colors;
