"""
A quick gradio app demo for my Notion RAG Chatbot.

Next Steps:
1. Display "retrieving context" intermediate thought process.
2. Deploy and host on HuggingSpace.
"""

import gradio as gr
from gradio import ChatMessage
from src.rag.rag_chat import RAGChat, ResponseFormat
import time
from typing import Generator

chatbot = RAGChat(retrieve_limit=3)
chatbot._instantiate_agents("gpt-4o")

def process_message(response: ResponseFormat) -> str:
    """Parse a structured response into a readable message."""
    parts = [
        response.message,
    ]
    # Properly display links
    if response.sources is not None:
        parts.append('\n' + '-' * 50 + " Sources " + '-' * 50)
        parts.extend(response.sources)
    result = '\n'.join(parts)
    print(result)
    return result


def chat_response(message, history) -> str:
    """Chat funciton for Gradio's chat interface."""
    response = chatbot.get_response(message)
    result = process_message(response)
    return result

def chat_stream(message, history) -> Generator[str, None, None]:
    """A chat funciton with streaming visuals for Gradio's chat interface."""
    response = chatbot.get_response(message)
    result = process_message(response)
    for i in range(len(result)):
        if result[i] not in {'\n', ' '}:
            time.sleep(0.01)
        yield result[:i+1]
        
def chat_full_visuals(message, history) -> ChatMessage:
    """A chat function for gradio that displays the chatbot's 
    thinking process as well as final message streaming."""

demo = gr.ChatInterface(
        fn=chat_stream,
        chatbot=gr.Chatbot(height=350),
        textbox=gr.Textbox(placeholder="Ask Me Anything, or Chat", container=False, scale=7),
        title="UTAT Space Systems Notion Chatbot",
        description="Ask questions regarding UTAT Space Systems, or just chat!",
        examples=[
            "What do you do?",
            "Optics meeting schedule?",
            "Options that we're considering for dark-frame acquisition of FINCH?"
            # "Current discussion on on-orbit dark frame calibration?",
            ],
        )

demo.launch()