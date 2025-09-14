from typing import Union

from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable
from pipecat.frames.frames import (
    LLMTextFrame,
    TextFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    TranscriptionFrame,
    StartInterruptionFrame,
    LLMMessagesFrame,
    Frame,
    TransportMessageUrgentFrame,
)
from pipecat.processors.frameworks.langchain import LangchainProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
import logging
import os
#from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from services.config import ( PROMPT, LLM_MODEL, GEMMINI_API_KEY )
logger = logging.getLogger(__name__)
from pipecat.processors.aggregators.llm_response import LLMUserContextAggregator, LLMAssistantContextAggregator
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame

from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)



'''
class LangchainRAGProcessor(LangchainProcessor):
    def __init__(self, prompt: str = PROMPT, index_name: str = "god-ai", transcript_key: str = "input", session_id:str = ""):
        
        self.set_participant_id(session_id)
        self._transcript_key = transcript_key
        self._session_id = session_id
        self._message_store = {}
        self.embedding_function = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            google_api_key=GEMMINI_API_KEY
        )
        self._vectorstore = PineconeVectorStore.from_existing_index(
            index_name=index_name, embedding=self.embedding_function
        )
        self._retriever = self._vectorstore.as_retriever(search_kwargs={"k": 3})
        self._prompt = self._build_prompt(prompt)
        self._llm = ChatGroq(model=LLM_MODEL)
        self._question_answer_chain = create_stuff_documents_chain(self._llm, self._prompt)
        self._rag_chain = create_retrieval_chain(self._retriever, self._question_answer_chain)
        self._chain = RunnableWithMessageHistory(
            self._rag_chain,
            self.get_session_history,
            history_messages_key="chat_history",
            input_messages_key="input",
            output_messages_key="answer",
        )
        super().__init__(self._chain, transcript_key)

    def _build_prompt(self, prompt: str):
        return ChatPromptTemplate.from_messages([
            ("system", prompt + "\n\n{context}"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

    def get_session_history(self) -> BaseChatMessageHistory:
        if self._session_id not in self._message_store:
            self._message_store[self._session_id] = ChatMessageHistory()
        return self._message_store[self._session_id]

    @staticmethod
    def __get_token_value(text: Union[str, AIMessageChunk]) -> str:
        match text:
            case str():
                return text
            case AIMessageChunk():
                return text.content
            case dict() as d if "answer" in d:
                return d["answer"]
            case _:
                return ""
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and handle LLM message frames.

        Args:
            frame: The incoming frame to process.
            direction: The direction of frame flow in the pipeline.
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMMessagesFrame):
            # Messages are accumulated on the context as a list of messages.
            # The last one by the human is the one we want to send to the LLM.
            logger.debug(f"Got transcription frame {frame}")
            text: str = frame.messages[-1]["content"]

            await self._ainvoke(text.strip())
        else:
            await self.push_frame(frame, direction)

    async def _ainvoke(self, text: str):
        await self.push_frame(LLMFullResponseStartFrame())
        try:
            print("messages-->", self._message_store[self._session_id])
            async for token in self._chain.astream(
                {self._transcript_key: text},
                config={"configurable": {"session_id": self._session_id}},
            ):
                await self.push_frame(LLMTextFrame(self.__get_token_value(token)))
        except GeneratorExit:
            logger.error(f"{self} generator was closed prematurely")
        except Exception as e:
            logger.error(f"{self} an unknown error occurred: {e}")
        finally:
            await self.push_frame(LLMFullResponseEndFrame())

    def handle_user_input(self, text):
        print("user input-->", text)
'''

class RAGProcessor(FrameProcessor):
    def __init__(self, *, name: str | None = None, prompt: str= PROMPT):
        super().__init__(name=name)
        self._prompt = prompt

    async def setup(self, setup):
        await super().setup(setup)
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, OpenAILLMContextFrame):
            #context: OpenAILLMContext = frame.context
            context:OpenAILLMContext = frame.context
            if context.messages and context.messages[0].get("content"):
                context.messages[0] = {"role": "system", "content": "testing"}
                

            await self.push_frame(
                OpenAILLMContextFrame(context=context),
                direction,
            )
        await self.push_frame(frame, direction)

    def _transform(self, frame: Frame) -> Frame:
        # e.g. add metadata, replace payload, wrap in a new Frame subclass…
        frame.metadata["seen_by_custom"] = True
        return frame
