import os
import asyncio
import websockets
import sys
from services.twilio import twilio_handler



def main():
	proxy_server = websockets.serve(twilio_handler, 'localhost', 5000)
	print('Server starting on ws://localhost:5000')
	asyncio.get_event_loop().run_until_complete(proxy_server)
	asyncio.get_event_loop().run_forever()
	

if __name__ == '__main__':
	sys.exit(main() or 0)