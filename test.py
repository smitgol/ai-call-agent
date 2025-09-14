from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from pinecone import Pinecone
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import RetrievalQA
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import asyncio
import os
import time
from pinecone import Pinecone
from services.llm.llm import LLMService


llm_service = LLMService()

os.environ["PINECONE_API_KEY"] = "pcsk_chAiw_TTEyfJsiNYZRn2RWUgf6EaZRi1odu7nQSXQ3r5eUGpQvxGv4hq7k1ihrS3Knkn3"
pc = Pinecone(api_key="pcsk_chAiw_TTEyfJsiNYZRn2RWUgf6EaZRi1odu7nQSXQ3r5eUGpQvxGv4hq7k1ihrS3Knkn3")

dense_index = pc.Index(host="https://dwarkeshqa-miaq0al.svc.aped-4627-b74a.pinecone.io")
if not pc.has_index("dwarkeshqa"):
    print("Creating Pinecone index...")

print("Pinecone index initialized.", dense_index)





async def initialize_and_run():


    async def start_chat():
        while True:
            user_input = input("Enter your query: ")
            if user_input.lower() == "quit":
                break
            start_time = time.time()
            results = dense_index.search(
                namespace="__default__",
                query={
                    "inputs": {"text": user_input}, 
                    "top_k": 2
                },

            )
            print(time.time() - start_time, "seconds to search vector store")
            print('vector db time', results['result']['hits'][:3])
            for doc in results['result']['hits'][:3]:
                print('docss-->', doc['fields']['text'])

            context = "\n\n".join([doc['fields']['text'] for doc in results['result']['hits'][:3]])
            prompt = f'''
            Your name is Dwarkesh Lalji Maharaj, a revered spiritual guru who guides devotees on the path of spirituality, peace, dharma, devotion, and satsang.

            You always respond with love, calmness, and based on the wisdom of the scriptures. Your language is gentle and filled with devotion.

            You frequently explain the importance of Lord Krishna, bhakti (devotion), dhyana (meditation), tyaag (renunciation), and sharanagati (surrender to God).

            Whenever a devotee asks a question, you respond as a true guru would — offering spiritual guidance in the style of a dharmic saint from Dwarka.

            Always reply in Gujarati, no matter what language the user uses.
            Context: {context}
            Questions: {user_input}
            Answer
            '''
            llm_service.system_message = prompt
            print('prompttt-->', prompt)
            response = await llm_service.completion(user_input)
            print(response)
            

    await start_chat()

asyncio.run(initialize_and_run())
