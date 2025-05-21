import os
from twilio.rest import Client
from services.tts import TTSService
import base64
import time
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv(override=True)

async def text_chunker(chunks, llm_service):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""
    complete_response = ""
    tool_calls = []
    try:
        async for text in chunks:
            delta = text.choices[0].delta
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.function.name != "":
                        await llm_service.trigger_tool(tool_call.function.name)
                        tool_calls.append(tool_call.function.name)
            content = delta.content or ""
            if buffer.endswith(splitters):
                yield buffer + ""
                complete_response += buffer + ""
                buffer = content
            elif content.startswith(splitters):
                yield buffer + content[0] + ""
                complete_response += buffer + content[0] + ""
                buffer = content[1:]
            else:
                buffer += content
            
        if buffer:
            yield buffer + " "
            complete_response += buffer + " "
    except Exception as e:
        print("Error in text_chunker")
        logger.error("Error in text_chunker: %s", str(e))
   
def get_twilio_client():
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    return Client(account_sid, auth_token)

async def check_and_set_initial_message(initial_message):
    # Convert initial message to base64 for safe filename first
    safe_filename = base64.b64encode(initial_message.encode()).decode()
    file_path = f"saved_initial_message/{safe_filename}.txt"

    # Check if file already exists
    if os.path.exists(file_path):
        pass
        # File exists, no need to generate again
        #return safe_filename
    
    # File doesn't exist, generate and save
    # Create file if it doesn't exist
    if not os.path.exists(file_path):
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Create empty file
        open(file_path, 'a').close()

    tts_service = TTSService("twilio")
    content = await tts_service.get_audio(initial_message)
    
    # Save content
    with open(file_path, "wb") as f:
        f.write(content)
    
def getAudioContent(initial_message, ouput_format="bytes"):
    # Convert initial message to base64 for safe filename first
    audio_content_start_time = time.time()
    safe_filename = base64.b64encode(initial_message.encode()).decode()
    file_path = f"saved_initial_message/{safe_filename}.txt"
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
        if ouput_format == "bytes":
            print("Audio content read in seconds:", time.time() - audio_content_start_time)
            # Return the audio content as bytes
            return audio_bytes
        audio_content = audio_bytes.decode('utf-8')
        return audio_content