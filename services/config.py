import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# API Keys
DEEPGRAM_API_KEY = os.environ['DEEPGRAM_API_KEY']
GROQ_API_KEY = os.environ['GROQ_API_KEY']
ELEVENLABS_API_KEY = os.environ['ELEVENLABS_API_KEY']

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']

#inital message
initial_message = "Namaskar app credit card kharidne me ruchi rakhte hai ?"

# Validate required environment variables
required_vars = [
    'DEEPGRAM_API_KEY',
    'GROQ_API_KEY',
    'ELEVENLABS_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN'
]

missing_vars = [var for var in required_vars if not os.environ[var]]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
