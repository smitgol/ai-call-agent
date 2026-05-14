# AI Call Agent with Deepgram

A sophisticated AI-powered voice call agent built with FastAPI, Pipecat, and multiple AI services for real-time voice interactions. This project enables automated customer support calls with natural language processing, speech-to-text, text-to-speech, and intelligent conversation management.

## 🚀 Features

- **Multi-Platform Support**: Twilio, Exotel, and WebSocket-based voice assistants
- **Real-time Voice Processing**: Speech-to-text and text-to-speech with low latency
- **AI-Powered Conversations**: Powered by Groq's Llama models for intelligent responses
- **Multiple TTS Providers**: ElevenLabs and Cartesia support
- **RAG Integration**: Retrieval-Augmented Generation for context-aware responses
- **Call Management**: Bulk calling, call recording, and transcription logging
- **MongoDB Integration**: Persistent storage for call configurations and transcripts
- **Docker Support**: Containerized deployment ready

## 🏗️ Architecture

The project is built using a modular architecture with the following key components:

```
├── main.py                          # FastAPI application entry point
├── services/
│   ├── core/
│   │   ├── pipecat_agent/          # Pipecat-based voice agents
│   │   │   ├── twilio_bot.py       # Twilio integration
│   │   │   ├── exotel_bot.py       # Exotel integration
│   │   │   ├── websocket_bot.py    # WebSocket voice assistant
│   │   │   └── rag_bot.py          # RAG-enabled bot
│   │   └── twilio/                 # Twilio-specific handlers
│   ├── llm/                        # Language model services
│   ├── stt/                        # Speech-to-text services
│   ├── tts/                        # Text-to-speech services
│   └── config.py                   # Configuration management
├── call_handlers/                  # Call management utilities
│   ├── make_call.py               # Single call initiation
│   ├── bulk_call.py               # Bulk calling functionality
│   ├── download_recording.py      # Recording management
│   └── append_transcription.py    # Transcription handling
└── campaign_files/                # Campaign data and recordings
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11
- **Voice Processing**: Pipecat AI, Deepgram, Groq
- **AI Services**: Groq (Llama models), ElevenLabs, Cartesia
- **Database**: MongoDB with Motor (async driver)
- **Telephony**: Twilio, Exotel
- **Deployment**: Docker, Uvicorn
- **Additional**: LangChain (RAG), Sentry (monitoring)

## 📋 Prerequisites

- Python 3.11+
- MongoDB instance
- API keys for:
  - Groq (for LLM)
  - ElevenLabs (for TTS)
  - Deepgram (for STT)
  - Twilio (for telephony)
  - Exotel (optional, for alternative telephony)
  - Cartesia (optional, for alternative TTS)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/smitgol/ai-call-agent.git
cd ai-call-agent-deepgram
```

### 2. Create Virtual Environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
GROQ_API_KEY=your_groq_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
CARTESIA_API_KEY=your_cartesia_api_key
OPENAI_API_KEY=your_openai_api_key
ASSEMBLY_API_KEY=your_assembly_api_key
GLADIA_API_KEY=your_gladia_api_key
GEMMINI_API_KEY=your_gemini_api_key

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
FROM_NUMBER=your_twilio_phone_number

# Exotel Configuration (Optional)
EXOTEL_ACCOUNT_SID=your_exotel_account_sid
EXOTEL_AUTH_KEY=your_exotel_auth_key
EXOTEL_AUTH_TOKEN=your_exotel_auth_token
EXOTEL_FROM_NUMBER=your_exotel_phone_number
EXOTEL_APP_ID=your_exotel_app_id

# Database
MONGO_DB_URL=mongodb://localhost:27017

# Server Configuration
SERVER=your_domain.com
PROD_SERVER=your_production_domain.com

# Monitoring
SENTRY_SDK_URL=your_sentry_dsn
KOALA_ACCESS_KEY=your_koala_access_key
```

### 5. Database Setup

Ensure MongoDB is running and accessible. The application will automatically create the required collections.

## 🚀 Running the Application

### Development Mode

```bash
python main.py
```

The application will start on `http://localhost:5000`

### Production Mode with Docker

```bash
# Build the Docker image
docker build -t ai-call-agent .

# Run the container
docker run -p 8080:8080 --env-file .env ai-call-agent
```

## 📡 API Endpoints

### WebSocket Endpoints

- `ws://localhost:5000/ws/handle_call` - Twilio call handling
- `ws://localhost:5000/ws/pipecat/{session_id}` - Pipecat Twilio integration
- `ws://localhost:5000/ws/voice-assistant/{session_id}` - WebSocket voice assistant
- `ws://localhost:5000/ws/telecmi` - Exotel call handling
- `ws://localhost:5000/rag_bot` - RAG-enabled bot

### REST API Endpoints

#### Call Management

**POST** `/start_call`
Initiate a Twilio call

```json
{
  "to_number": "+1234567890",
  "prompt": "Custom system prompt",
  "language": "en",
  "voice_id": "voice_id",
  "initial_message": "Hello, how can I help you?"
}
```

**POST** `/start_call_exotel`
Initiate an Exotel call

```json
{
  "to_number": "+1234567890",
  "prompt": "Custom system prompt",
  "language": "en",
  "voice_id": "voice_id",
  "initial_message": "Hello, how can I help you?"
}
```

**POST** `/create_voice_assistant_session`
Create a WebSocket voice assistant session

```json
{
  "prompt": "Custom system prompt",
  "language": "en",
  "voice_id": "voice_id",
  "initial_message": "Hello, how can I help you?"
}
```

**POST** `/handle-call`
Twilio webhook for call handling

**GET** `/`
Health check endpoint

## 🤖 AI Agent Configuration

The AI agent is configured as "Mira," a customer support specialist for Voycia. Key features:

- **Role**: AI-powered Customer Support Specialist
- **Capabilities**: 
  - Automate high-volume support calls
  - Handle order tracking, FAQs, refunds, appointment scheduling
  - Multilingual voice interactions
  - Real-time intent recognition
  - Custom scripting and brand personalization
  - 24/7 availability with live agent fallback

### Customizing the Agent

Modify the `PROMPT` variable in `services/config.py` to customize the agent's behavior, personality, and capabilities.

## 📞 Call Handlers

### Single Call (`call_handlers/make_call.py`)
Initiate individual calls with custom parameters.

### Bulk Calling (`call_handlers/bulk_call.py`)
Process Excel files for bulk calling campaigns with configurable batch sizes and delays.

### Recording Management (`call_handlers/download_recording.py`)
Download and manage call recordings from Twilio.

### Transcription (`call_handlers/append_transcription.py`)
Handle and process call transcriptions.

## 🔧 Configuration

### Voice Settings

- **TTS Voice ID**: Configured in `services/config.py`
- **Language Support**: Multiple languages supported via ElevenLabs and Cartesia
- **Sample Rate**: 8kHz for telephony, configurable for other use cases

### LLM Settings

- **Model**: `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **Temperature**: 0.7
- **Max Tokens**: 1000
- **Tools**: Call termination functionality

### Database Schema

The application uses MongoDB with the following collections:
- `call_configs`: Call session configurations
- `transcripts`: Call transcriptions and logs

## 🚀 Deployment

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t ai-call-agent .
```

2. Run with environment variables:
```bash
docker run -p 8080:8080 --env-file .env ai-call-agent
```

### Environment Variables for Production

Ensure all required environment variables are set in your production environment, particularly:
- All API keys
- Database connection string
- Server domain
- Telephony credentials

## 📊 Monitoring and Logging

- **Logging**: Configured via `logger_config.py`
- **Sentry Integration**: Error tracking and performance monitoring
- **Call Metrics**: Built-in usage metrics and performance tracking

## 🔍 Troubleshooting

### Common Issues

1. **WebSocket Connection Issues**: Ensure proper CORS configuration and WebSocket URL formatting
2. **Audio Quality Issues**: Check sample rate configuration and TTS provider settings
3. **API Rate Limits**: Monitor usage across all integrated services
4. **Database Connection**: Verify MongoDB connectivity and credentials

### Debug Mode

Enable debug logging by modifying the logging configuration in `logger_config.py`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

## 🔄 Version History

- **v1.0.0**: Initial release with Twilio and Exotel integration
- **v1.1.0**: Added RAG support and WebSocket voice assistant
- **v1.2.0**: Enhanced with multiple TTS providers and improved error handling

---

**Note**: This project requires valid API keys for all integrated services. Ensure you have proper subscriptions and rate limits configured for production use.
