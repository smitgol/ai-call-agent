from langchain_pinecone import PineconeVectorStore
#from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
os.environ["PINECONE_API_KEY"] = os.environ.get("PINECONE_API_KEY")
#embed_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.environ.get("GEMMINI_API_KEY"))

#vectorstore = PineconeVectorStore.from_existing_index(
#    index_name="god-ai", embedding=embed_model
#)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Smaller chunks for better granularity
    chunk_overlap=200,  # Overlap to preserve context
    length_function=len
)
batch_size = 100

def load_document(file_path):
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".md"):
        loader = UnstructuredMarkdownLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path)
    document_content = loader.load()
    chunks = text_splitter.split_documents(document_content)
    return chunks


def add_document(chunks):
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        #vectorstore.add_documents(documents=batch)


#def search(query):
#    retriever = vectorstore.as_retriever()
#    return vectorstore.similarity_search(query=query)


if __name__ == "__main__":
    documents_to_add = [
        "Svetasvatara_Upanishad.md",
        "ling_puran_part_1.md",
        "ling_puran_part_2.md",
    ]
    #for document in documents_to_add:
    #    chunks = load_document(document)
    #    add_document(chunks)
    #    print("Documents added to Pinecone -->", document)
    #print(search("what is the purpose of life?"))