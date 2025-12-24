from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from uuid import uuid4
import shutil

from dotenv import load_dotenv
import os


# Load text docs
texts = []
for filename in os.listdir('text_docs'):
    file_path = os.path.join('text_docs', filename)

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
        texts.append(text)


text_splitter = RecursiveCharacterTextSplitter(
    # Set a really small chunk size, just to show.
    chunk_size=5000,
    chunk_overlap=20,
    length_function=len,
    is_separator_regex=False,
)
documents = text_splitter.create_documents(texts)
# print(documents[0])
# print(documents[1])


# Load api key
load_dotenv()
key = os.environ.get("OPENAI_API_KEY")
# Create embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)
print("embeddings created")

# Remove data base since we want to create one from scratch
shutil.rmtree("./chroma_langchain_db")

# Vector store
vector_store = Chroma(
    collection_name="my_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

# Add documents to vector store (embedded automatically when added)
uuids = [str(uuid4()) for _ in range(len(documents))]
vector_store.add_documents(documents=documents, ids=uuids)