import os
from twilio.rest import Client
from services.tts.tts import TTSService
import base64
import time
from dotenv import load_dotenv
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from services.config import MONGO_DB_URL
import requests



client = AsyncIOMotorClient(MONGO_DB_URL)
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


def call_exotel_api(to_number, session_id):
    url = f"https://api.exotel.com/v1/Accounts/{os.environ.get('EXOTEL_ACCOUNT_SID')}/Calls/connect"

    payload = {
        'From': to_number,
        'CallerId': os.environ["EXOTEL_FROM_NUMBER"],
        'Url': f'http://my.exotel.com/{os.environ.get("EXOTEL_ACCOUNT_SID")}/exoml/start_voice/' + os.environ.get("EXOTEL_APP_ID"),
        'CustomField': 'session_id=' + session_id,
    }

    response = requests.request("POST", url, auth=(os.environ.get("EXOTEL_AUTH_KEY"), os.environ.get("EXOTEL_AUTH_TOKEN")), data=payload)
    print("Exotel API response:", response.text)
    return response.status_code
    
def getAudioContent(initial_message, type="string"):
    # Convert initial message to base64 for safe filename first
    safe_filename = base64.b64encode(initial_message.encode()).decode()
    file_path = f"saved_initial_message/{safe_filename}.txt"
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
        audio_content = audio_bytes.decode('utf-8')
        if type == "bytes":
            return audio_bytes
        return audio_content
    
def getDb():
    db = client.ai_call_agent
    return db