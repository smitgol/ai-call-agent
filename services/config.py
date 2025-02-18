import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# Validate required environment variables
required_vars = [
    'DEEPGRAM_API_KEY',
    'GROQ_API_KEY',
    'ELEVENLABS_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
