from groq import AsyncGroq
from services.event_emmiter import EventEmitter
from services.config import GROQ_API_KEY, PROMPT, LLM_MODEL  # Changed from relative to absolute import
import logging

logger = logging.getLogger(__name__)

GROQ_API_KEY = GROQ_API_KEY


tool_list = [
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "Ends the current phone call or conversation",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }        
        },
    }
]

    

class LLMService(EventEmitter):
    def __init__(self):
        super().__init__()
        self.system_message = PROMPT
        self.user_context = [
            {"role": "system", "content": self.system_message}
        ]
        self.llm = AsyncGroq(api_key=GROQ_API_KEY)
        self.model = LLM_MODEL

    async def completion(self, text):
        try:
            self.user_context.append({"role": "user", "content": text})
            stream = await self.llm.chat.completions.create(
                model=self.model,
                messages=self.user_context,
                stream=True,
                max_tokens=1000,
                temperature=0.7,
                tools=tool_list,
                tool_choice="auto",)
            complete_response = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                complete_response += content
            await self.emit('llm_response', complete_response)

            self.user_context.append({"role": "assistant", "content": complete_response})
        except Exception as e:
            print("Error generating LLM response:", str(e))
            return None
        
    async def complete_with_chunks(self, text):
        try:
            self.user_context.append({"role": "user", "content": text})
            stream = await self.llm.chat.completions.create(
                model=self.model,
                messages=self.user_context,
                stream=True,
                max_tokens=500,
                temperature=0.7,
                tools=tool_list,
                tool_choice="auto",)
            await self.emit('llm_stream', stream)

        except Exception as e:
            print("Error generating LLM response:", str(e))
            return None
    
    async def trigger_tool(self, tool_name):
        try:
            logger.info(f"tool_triggered : {tool_name}")
            await self.emit('tool_triggered', tool_name)
        except Exception as e:
            print("Error triggering tool:", str(e))
            return None


