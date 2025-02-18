from groq import AsyncGroq
from services.event_emmiter import EventEmitter
from .config import GROQ_API_KEY

GROQ_API_KEY = GROQ_API_KEY

prompt = f"you are ai call agent that perform sale operation. \nyou have to sale credit card \nif user is not interested try convincing them one more time \nHere is the card detail\n--> No annual charge \n--> get airport lounge service once every quarter  \nDpnt tell card detail one first message\nYou have to talk in hindi.Keep your answer short and simple.keep your answer under 50 words"
    

class LLMService(EventEmitter):
    def __init__(self):
        super().__init__()
        self.system_message = prompt
        self.user_context = [
            {"role": "system", "content": self.system_message}
        ]
        self.llm = AsyncGroq(api_key=GROQ_API_KEY)
        self.model = "llama-3.2-3b-preview"

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



