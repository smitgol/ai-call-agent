from services.llm import LLMService
from services.tts import TTSService
from utils import text_chunker
import asyncio  # Add this import
from services.call_transcription import TranscriptionLogger
import time
import json

llm_service = LLMService()

tts_service = TTSService("twilio")

tts_task = None

async def handle_llm_response(response, llm_start_time):
    complete_sentence = ""
    print("LLM response started...")
    #async for text in text_chunker(text_iterator, llm_service):
    #    complete_sentence += text
    #    print(text, end="", flush=True)  # Print the text as it comes in
    llm_service.user_context.append({"role": "assistant", "content": response}) #pushing the complete sentence to user context
    print(f"LLM response: {response}")
    print(f"LLM response time: {time.time() - llm_start_time:.2f} seconds")
    

async def test_llm_and_tts_with_completion():
    global tts_task  # Use global instead of nonlocal
    """
    Gets user input from terminal and processes it through the LLM service.
    Returns the LLM response.
    """
    async def on_llm_stream(text_iterator):  # Define the callback to pass llm_start_time
        await handle_llm_response(text_iterator, llm_start_time)
    try:
        while True:
            # Get user input from terminal
            user_input = input("Please enter your message (or 'quit' to exit): ")
            
            # Check if user wants to quit
            if user_input.lower() == 'quit':
                break
            
            llm_start_time = time.time()

            llm_service.on('llm_response', on_llm_stream)
            
            # Call the LLM service with user input
            await llm_service.completion(user_input)
            
            # Print the response
            print()  # Empty line for readability
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

async def test_llm_and_tts_with_streaming():

    async def tts_listener():
        print("TTS streaming started...")
        while True:
            try:
                audio_chunk = await tts_service.tts_ws.recv()
                if audio_chunk:
                    # Process the audio chunk here
                    print("Received audio chunk:")
                else:
                    break  # Exit the loop if no more audio chunks are received
            except websockets.ConnectionClosed:
                print("Connection closed")
                break
        print("TTS streaming completed.")
        tts_task.cancel()          # Cancel the TTS task after streaming is done

    async def handle_llm_stream(response, llm_start_time):
        complete_sentence = ""
        tts_task = asyncio.create_task(tts_listener())
        async for text in text_chunker(response, llm_service):
            print("text chunk", text)
            await tts_service.tts_ws.send(json.dumps({"text": text}))
            complete_sentence += text
        if tts_service.tts_ws:
            await tts_service.end_tts_streaming(tts_service.tts_ws)
            print("TTS streaming completed.")
        llm_service.user_context.append({"role": "assistant", "content": complete_sentence}) 
            

    async def on_llm_stream(text_iterator):  # Define the callback to pass llm_start_time
        await handle_llm_stream(text_iterator, llm_start_time)
    try:
        while True:
            # Get user input from terminal
            user_input = input("Please enter your message (or 'quit' to exit): ")
            
            # Check if user wants to quit
            if user_input.lower() == 'quit':
                break
            
            llm_start_time = time.time()
            await tts_service.connect_tts()
            llm_service.on('llm_stream', on_llm_stream)
            
            # Call the LLM service with user input
            await llm_service.complete_with_chunks(user_input)
            
            # Print the response
            print()  # Empty line for readability
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

async def test_saving_transcription():
    trans = TranscriptionLogger("test_call_sid")
    arr= [(1744305841.0088525, 'STT', ' Hello.'), (1744305844.0213773, 'LLM', 'नमस्ते! कैसे हैं आप? क्या आपने ग्राफिक डिजाइनिंग कोर्स के लिए enquiry सबमिट की थी?'), (1744305855.2382889, 'STT', ' नहीं.'), (1744305856.134704, 'LLM', 'क्या आप ग्राफिक डिजाइनिंग, एनिमेशन, VFX या वेब डिजाइनिंग सीखना चाहते हैं?'), (1744305863.3336813, 'STT', ' नहीं मुझे नहीं चाहिए.'), (1744305863.5857246, 'LLM', 'ठीक है, कोई बात नहीं। धन्यवाद! \n\n\n<end_call> ')]
    trans.entries = arr
    await trans.save_to_file()
    print("Transcription saved successfully.")
    

if __name__ == "__main__":
    # Run the async function using asyncio
    asyncio.run(test_llm_and_tts_with_streaming())