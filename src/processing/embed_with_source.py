"""Contain functions that load json files, split text into chunks (LangChain `Document` objects)
with source url attached, embed them, and store them into a chroma vector store."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from uuid import uuid4
import shutil

from dotenv import load_dotenv
import os
import time
import json

from src.file_config import *


def load_json_from_dir(dir_path: str) -> list[dict[str, str]]:
    """
    Given a directory path, load all .json files into dictionary mappings.
    """
    # Load text docs
    collection = []
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)

        with open(file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            collection.append(mapping)
    return collection

def split_content(collection: list[dict[str, str]], chunk_size: int = 512) -> list[Document]:
    """Split given list of mappings into langchain `Document` object. Each object
    will have metadata attr "source" mapping to the correct url.
    Chunk size is the number of characters each splitted chunk should contain.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=20,
        length_function=len,
        is_separator_regex=False,
    )
    
    documents = []
    for mapping in collection:
        text = mapping.get("text")
        source = mapping.get("source")
        
        documents.extend(
            text_splitter.create_documents(
                texts=[text], 
                metadatas=[{"source": source}]
            )
        )
    
    # print(documents[1])

    return documents


def embed_and_store(docs: list[Document], fresh_store: bool = False) -> None:
    """Given a list of langchain `Document` objects, embed them and store them
    into a chroma database saved at persist_dir. If fresh_store is set to True,
    the old persist_dir will be first removed.
    """
    # Load api key
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")
    # Create embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)
    print("Embeddings Created")

    # Remove database if mode is fresh
    if fresh_store:
        confirm = input("Are you sure you want to erase previous database? " \
        "Type 'yes' to continue: ")
        if confirm:
            shutil.rmtree(DB_DIR)
        else:
            print("Switched to add mode. Adding new docs to database...")
            time.sleep(5)

    # Vector store
    vector_store = Chroma(
        collection_name="my_collection",
        embedding_function=embeddings,
        persist_directory=DB_DIR,
    )

    uuids = [str(uuid4()) for _ in range(len(docs))]
    batch_size = 5461    # max batch size for chromadb to embed and store at once
    
    docs_batches = [docs[i:i+batch_size] for i in range(0, len(uuids), batch_size)]
    uuids_batches = [uuids[i:i+batch_size] for i in range(0, len(uuids), batch_size)]
    
    # Add documents batch by batch to vector store (embedded automatically when added)
    for i in range(len(uuids_batches)):
        docs_batch, uuids_batch = docs_batches[i], uuids_batches[i]
        vector_store.add_documents(documents=docs_batch, ids=uuids_batch)
    
    print("Documents successfully embedded and added to vector store.")

if __name__ == '__main__':
    embed_and_store(
        split_content(
            load_json_from_dir(JSON_DIR)
        ),
        fresh_store=True
    )