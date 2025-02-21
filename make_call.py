# twilio helper library
from twilio.rest import Client

# other imports
import time
import requests
import json
import os
import uuid


# make the outgoing call
from twilio.rest import Client
from services.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
# Your Twilio credentials
account_sid = TWILIO_ACCOUNT_SID
auth_token = TWILIO_AUTH_TOKEN
to_number = os.getenv('TO_NUMBER')
from_number = os.getenv('FROM_NUMBER')
stream_url = os.getenv('STREAM_URL')
client = Client(account_sid, auth_token)


# Define your TwiML instructions – note the <Stream> URL points to your WebSocket endpoint.
twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="hi-IN">Namaskar Me AI Agent Hu</Say>
  <Connect>
    <Stream url="wss://{stream_url}" />
  </Connect>
</Response>"""


# Create a call
call = client.calls.create(
    twiml=twiml,  # Ensure proper placement of <Stream>
    to=to_number,  # Person A
    from_=from_number  # Your Twilio number
)

