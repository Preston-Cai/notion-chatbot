# Notion Chatbot
- Deep-crawling dynamic JS-support web scraper to find all subpages of a given URL: `src/scraping/scrape.py`.
- Content chunking, NLP embedding, and vector storing pipeline: `src/processing/`
- An RAG chatbot that can answer questions based on context retrieved from a chroma database: `src/rag/rag_chat.py`.
- Gradio demo app: `gradio_app/app.py`.
- Development journal: [Journal](development-journal.md)

## Introduction

As an organization grows large, the huge Notion workplace can be incredibly difficult to navigate, with possibly *thousands* of pages. A context-aware chatbot can help answer organization- or mission- specific questions, thus born this project.

The project consists of three stages: scraping all Notion subpages of a URL recursively, chunking documents and creating/storing NLP vector embeddings, and orchestrating retrieval-augmented agent.

## Major Libraries/Frameworks Used
1. Dynamic Recursive Web Scraping: Playwright, Beautiful Soup
2. Embedding/Vector Storing: LangChain, OpenAI API, Chroma
3. RAG Agent Flow: LangChain, LangGraph, OpenAI API
4. Demo App: Gradio, Hugging Face

## Quick Start: make your own RAG chatbot
In your desired directory, clone the repo:
```
git clone https://github.com/Preston-Cai/notion-chatbot
```
Install dependencies:
```
pip install -r requirements.txt
```
If failed, try loosening the dependencies.

### 0. Config
Since this project uses OpenAI API for embedding and LLM inference, it does not support other API (for now).\
To config your OpenAI API key, run the following commands in your project root:
```
echo OPENAI_API_KEY = '#put your api key here in this pair of quotes' > .env
```

### 1. Scraping
To scrap an URL recursively (dynamic JS supported):
1. In `src/scraping/scrape.py`, scroll down to the main block. Change the parameters.
2. To run: 
```
python -m src.scraping.scrape
```
3. For a URL with around 1000 children links, for `cap=8` it should take around 30 minutes.
4. Find the data in `data/scraping`.

### 2. Chunking/Embedding/Vector Storing
Chunk, embed, and vector store the content in `data/scraping` that was generated previously.
#### For `data/scraping/json_docs`
Recommended approach, as generated JSON docs contain the sources RAG agent needs to generate the correct response format.
To run:
```
python -m src.processing.embed_with_source
```
#### For `data/scraping/text_docs`
Not recommended for later RAG agent workflow.
To run:
```
python -m src.processing.embed_no_source
```

### 3. Launching RAG Chatbot
To config the context and prompt for your chatbot:
1. Open up src/rag/rag_chat.py and edit SYSTEM_PROMPT and the interface (docstring and decorator description) of the _retrieve_context tool with the @tool decorator.
2. Create a file `data/context/big_context.json` and enter your big-picture context for your chatbot. Ideally the content should be in JSON dict format, but the app won't break if it isn't.

To simulate a terminal chat loop, run in terminal:
```
python -m src.rag.rag_chat
```
To open gradio demo app in browser, run in terminal:
```
python -m gradio_app.app
```

This demo has been made private due to privacy concern: [notion-chatbot](https://huggingface.co/spaces/preston-cai/notion-chatbot)

## Project Tree
```
📦 
├─ .gitattributes
├─ .gitignore
├─ README.md
├─ development-journal.md
├─ experimental_legacy/     # experimental/exploratory files
├─ experimental_requirements.txt    # requirements for experimental files
├─ gradio_app
│  └─ app.py
├─ requirements.txt
└─ src
   ├─ __init__.py
   ├─ file_config.py
   ├─ processing/
   ├─ rag/
   ├─ scraping/
   ├─ tests/
   └─ utils/
```