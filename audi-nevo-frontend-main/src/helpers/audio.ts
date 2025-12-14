export const getAverageVolume = (array: Uint8Array) => {
    let values = 0;
    for (let i = 0; i < array.length; i++) {
        values += array[i];
    }
    return values / array.length;
};
