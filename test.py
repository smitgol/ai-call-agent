from services.llm import LLMService
from utils import text_chunker
import asyncio  # Add this import
from services.call_transcription import TranscriptionLogger
import time

llm_service = LLMService()

async def handle_llm_response(response, llm_start_time):
    complete_sentence = ""
    print("LLM response started...")
    #async for text in text_chunker(text_iterator, llm_service):
    #    complete_sentence += text
    #    print(text, end="", flush=True)  # Print the text as it comes in
    llm_service.user_context.append({"role": "assistant", "content": response}) #pushing the complete sentence to user context
    print(f"LLM response: {response}")
    print(f"LLM response time: {time.time() - llm_start_time:.2f} seconds")
    

async def get_user_input_and_process():
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


async def test_saving_transcription():
    trans = TranscriptionLogger("test_call_sid")
    arr= [(1744305841.0088525, 'STT', ' Hello.'), (1744305844.0213773, 'LLM', 'नमस्ते! कैसे हैं आप? क्या आपने ग्राफिक डिजाइनिंग कोर्स के लिए enquiry सबमिट की थी?'), (1744305855.2382889, 'STT', ' नहीं.'), (1744305856.134704, 'LLM', 'क्या आप ग्राफिक डिजाइनिंग, एनिमेशन, VFX या वेब डिजाइनिंग सीखना चाहते हैं?'), (1744305863.3336813, 'STT', ' नहीं मुझे नहीं चाहिए.'), (1744305863.5857246, 'LLM', 'ठीक है, कोई बात नहीं। धन्यवाद! \n\n\n<end_call> ')]
    trans.entries = arr
    await trans.save_to_file()
    print("Transcription saved successfully.")
    

if __name__ == "__main__":
    # Run the async function using asyncio
    asyncio.run(get_user_input_and_process())