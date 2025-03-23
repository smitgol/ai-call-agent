from groq import AsyncGroq
from services.event_emmiter import EventEmitter
from services.config import GROQ_API_KEY, PROMPT  # Changed from relative to absolute import

GROQ_API_KEY = GROQ_API_KEY

    

class LLMService(EventEmitter):
    def __init__(self):
        super().__init__()
        self.system_message = PROMPT
        self.user_context = [
            {"role": "system", "content": self.system_message}
        ]
        self.llm = AsyncGroq(api_key=GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"

    async def completion(self, text):
        try:
            self.user_context.append({"role": "user", "content": text})
            stream = await self.llm.chat.completions.create(
                model=self.model,
                messages=self.user_context,
                stream=True,
                max_tokens=125,
                temperature=0.7,)
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
                max_tokens=125,
                temperature=0.7,)
            await self.emit('llm_stream', stream)

        except Exception as e:
            print("Error generating LLM response:", str(e))
            return None



