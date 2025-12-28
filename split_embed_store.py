"""Contain functions that load texts, split texts into chunks (`Document` objects),
embed them, and store them into a chroma vector store."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from uuid import uuid4
import shutil

from dotenv import load_dotenv
import os
import time


def load_texts_from_dir(dir_path: str) -> list[str]:
    """
    Given a directory path, load all .txt files inot a list of strings.
    """
    # Load text docs
    texts = []
    for filename in os.listdir('text_docs'):
        file_path = os.path.join('text_docs', filename)

        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            texts.append(text)
    return texts

def split_text(texts: list[str], chunk_size: int = 512) -> list[Document]:
    """Split given list of strings into langchain `Document` object.
    Chunk size is the number of characters each splitted chunk should contain.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=20,
        length_function=len,
        is_separator_regex=False,
    )
    documents = text_splitter.create_documents(texts)
    # print(documents[0])
    # print(documents[1])

    return documents


def embed_and_store(docs: list[Document], fresh_store: bool = False,
                    persist_dir: str = "./chroma_langchain_db") -> None:
    """Given a list of langchain `Document` objects, embed them and store them
    into a chroma database saved at persist_dir. If fresh_store is set to True,
    the old persist_dir will be first removed.
    """
    # Load api key
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")
    # Create embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)
    print("embeddings created")

    # Remove database if mode is fresh
    if fresh_store:
        confirm = input("Are you sure you want to erase previous database? " \
        "Type 'yes' to continue.")
        if confirm:
            shutil.rmtree(persist_dir)
        else:
            print("Switched to add mode. Adding new docs to database...")
            time.sleep(5)

    # Vector store
    vector_store = Chroma(
        collection_name="my_collection",
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    # Add documents to vector store (embedded automatically when added)
    uuids = [str(uuid4()) for _ in range(len(docs))]
    vector_store.add_documents(documents=docs, ids=uuids)

if __name__ == '__main__':
    embed_and_store(
        split_text(
            load_texts_from_dir('text_docs')
        ), 
        fresh_store=True
    )