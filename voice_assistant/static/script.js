let isRecording = false;
let websocket;
let microphone;
const ws_port = 5000;
document.addEventListener("DOMContentLoaded", () => {
  const recordButton = document.getElementById("record");
  
  // Initialize WebSocket connection
  websocket = new WebSocket(
    "ws://" + window.location.href + ":" + ws_port.toString() + "/ws/voice-assistant"
  );

  // Handle incoming messages
  websocket.onmessage = (event) => {
    try {
      if (typeof event.data === "string") {
        try {
          const data = JSON.parse(event.data);
          if (data.transcription) {
            document.getElementById("captions").innerHTML = data.transcription;
          }
        } catch (error) {
          console.error("Error parsing JSON message:", error);
        }
      }
      // If it's not a string, treat it as binary audio data
      else if (event.data instanceof Blob) {
        // Create a URL for the received audio blob
        const audioUrl = URL.createObjectURL(event.data);
        
        // Check if an audio element already exists, or create a new one
        /*
        let audioPlayer = document.getElementById("audioPlayer");
        if (!audioPlayer) {
          audioPlayer = document.createElement("audio");
          audioPlayer.id = "audioPlayer";
          audioPlayer.controls = true;
          document.body.appendChild(audioPlayer);
        }
        
        // Set the source of the audio element to the Blob URL
        audioPlayer.src = audioUrl;
        audioPlayer.play().catch(err => console.error("Error playing audio:", err));
        */
        const mySound = new Audio(audioUrl);
        mySound.play();
      }
    } catch (error) {
      console.error("Error parsing WebSocket message:", error);
    }
  };

  // Handle connection errors
  websocket.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  // Handle connection close
  websocket.onclose = () => {
    console.log("WebSocket connection closed");
  };

  recordButton.addEventListener("click", () => {
    if (!isRecording) {
      // Send start command
      websocket.send(JSON.stringify({ action: "start" }));
      startRecording().catch((error) =>
        console.error("Error starting recording:", error)
      );
    } else {
      // Send stop command
      websocket.send(JSON.stringify({ action: "stop" }));
      stopRecording().catch((error) =>
        console.error("Error stopping recording:", error)
      );
    }
  });
});

async function getMicrophone() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return new MediaRecorder(stream, { mimeType: "audio/webm" });
  } catch (error) {
    console.error("Error accessing microphone:", error);
    throw error;
  }
}

async function openMicrophone(microphone) {
  return new Promise((resolve) => {
    microphone.onstart = () => {
      console.log("Client: Microphone opened");
      document.body.classList.add("recording");
      resolve();
    };
    
    microphone.ondataavailable = async (event) => {
      if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
        // Send audio data as binary
        websocket.send(event.data);
      }
    };
    
    microphone.start(1000);
  });
}

async function startRecording() {
  isRecording = true;
  microphone = await getMicrophone();
  console.log("Client: Waiting to open microphone");
  await openMicrophone(microphone);
}

async function stopRecording() {
  if (isRecording === true) {
    microphone.stop();
    microphone.stream.getTracks().forEach((track) => track.stop());
    microphone = null;
    isRecording = false;
    console.log("Client: Microphone closed");
    document.body.classList.remove("recording");
  }
}