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

service_url = f"https://{os.getenv('SERVER')}/handle-call"

# Validate required environment variables
if not to_number or not from_number:
    raise ValueError("TO_NUMBER or FROM_NUMBER environment variable is missing!")

# Create a call
call = client.calls.create(
    to=to_number,  # Person A
    from_=from_number,  # Your Twilio number
    url=service_url
)

