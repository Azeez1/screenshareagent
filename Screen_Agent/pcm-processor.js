// PCMProcessor: This is a special audio helper that works inside the browser.
// It helps us process audio data in real time, which is super useful for live voice interactions.
class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        // this.buffer is like a temporary storage box where we keep the audio data we receive.
        this.buffer = new Float32Array();

        // this part listen for messages sent to it
        // when a new message arrives it will execute the code inside
        this.port.onmessage = (e) => {
             // When a new message comes in, it contains audio data (newData)
            const newData = e.data;
            // We make a new, bigger storage box that can fit both the old data and the new data.
            const newBuffer = new Float32Array(this.buffer.length + newData.length);
             // put the old data in the new storage box
            newBuffer.set(this.buffer);
            // put the new data in the new storage box, right after the old data.
            newBuffer.set(newData, this.buffer.length);
            // Now, our storage box is updated to hold all the data, and we're ready for more!
            this.buffer = newBuffer;
        };
    }
    // this is a important function that helps in processeing the audio
    // it will take the stored data and pass it to the speakers
    process(inputs, outputs, parameters) {
         // This is where we send the processed audio data out.
        // 'output' is like the pipe that leads to the speakers or any other audio output.
        const output = outputs[0];
        // 'channelData' is like the information in the pipe that will go to the speaker
        const channelData = output[0];

        // we check if we have more audio data than the pipe can handle at once.
        if (this.buffer.length >= channelData.length) {
           // if there is enough data in buffer, we will copy it to the pipe
            channelData.set(this.buffer.slice(0, channelData.length));
            //after we send the data we remove it from our buffer
            this.buffer = this.buffer.slice(channelData.length);
            // this part will tell the computer that more data need to be sent
            return true;
        }

        return true;
    }
}

// this will tell the browser that this part will handle audio processing
registerProcessor('pcm-processor', PCMProcessor);