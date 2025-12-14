import {useEffect, useState} from "react";
import {useAtom} from "jotai/index";
import {receivedMessageAtom} from "../../store/atoms.ts";
import {ICar} from "../../types/ICar.ts";
import {API_URL} from "../../constants/constants.ts";


const CarShowroom = () => {
    const [receivedMessage] = useAtom(receivedMessageAtom);
    const [car, setCar] = useState<ICar>();
    useEffect(() => {

        if (receivedMessage) {
            try {
                const parsedData = JSON.parse(receivedMessage);
                
                // Handle show_image message format from backend
                if (parsedData.type === 'show_image') {
                    // Convert image path to full URL
                    // Backend sends paths like "audi/car_views/..." 
                    // Try to load from backend static files first, then fallback to public folder
                    let imageUrl = parsedData.image || '';
                    if (imageUrl) {
                        if (imageUrl.startsWith('http')) {
                            // Already a full URL, use as-is
                            // Do nothing
                        } else if (imageUrl.startsWith('/')) {
                            // Already starts with /, use as-is (public folder)
                            // Do nothing
                        } else {
                            // Path like "audi/car_views/..." - try backend static files first
                            imageUrl = `${API_URL}/static/${imageUrl}`;
                        }
                    }
                    
                    // Convert show_image format to ICar format
                    const carData: ICar = {
                        id: 0, // Default ID
                        image: imageUrl,
                        colorName: parsedData.text || 'Car',
                        colorOptions: parsedData.colorOptions || [], // Default to empty array if not provided
                        price: 0, // Default price
                    };
                    setCar(carData);
                } else {
                    // Assume it's already in ICar format
                    const carData: ICar = parsedData;
                    // Ensure colorOptions exists
                    if (!carData.colorOptions) {
                        carData.colorOptions = [];
                    }
                    setCar(carData);
                }
            } catch (error) {
                console.error('Failed to parse receivedMessage', error);
            }
        }
    }, [receivedMessage]);
    return (
        <>
            {car && <>
                <div key={`color-name-${car.id}`} className={''}>
                    <div className={'text-[#f0f0f0b0] font-bold text-5xl'}>
                    </div>
                </div>

                <div key={`car-image-${car.id}`} className={'w-full'}>
                    <>
                        <img src={car.image} alt={`${car.colorName}`} width={'100%'}/>
                    </>
                </div>
            </>}

            <div className="flex justify-center space-x-4 mt-4">
                {car && car.colorOptions && car.colorOptions.map((color, index) => (
                    <div
                        key={index}
                        className="w-10 h-10 rounded-full relative"
                        style={{backgroundColor: color}}
                    >
                        {/* Add a radial gradient for the center shine */}
                        <div
                            className="absolute inset-0 bg-radial-gradient(from-white/10, to-transparent) rounded-full"></div>
                        {/* Add a sharp top gradient to mimic lighting */}
                        <div
                            className="absolute inset-0 bg-gradient-to-b from-white/70 via-transparent to-transparent rounded-full"></div>
                        {/* Outer shadow for depth */}
                        <div className="absolute inset-0 rounded-full shadow-md"></div>
                    </div>
                ))}
            </div>


            {/*{ car.colorOptions && <Colors colors={car.colorOptions}/>}*/}
        </>
    );
};

export default CarShowroom;
