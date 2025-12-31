# Development Journal

## Web Scraping

### Tools Attempted for Scraping Notion
1. Basic requests
2. Scrapling dynamic fetcher (customized library on GitHub)
3. Selenium
4. Playwright (finally works)

### Parsing/Processing
1. Beautiful Soup

### Algorithms
1. Recursion with constraint (to get all subpages within the base url range)
2. Iterative queue list (to solve recursion limit issue)
3. Async programming (to speed up by opennign multiple tasks)
4. Round robin (to reuse open tabs and avoid overflow)

### Major Issues Solved
1. Make sure the page is fully loaded before extracting (sleep + scroll loop)
2. Let the browser stay open (OOP design)
3. Find hidden links through clickables, etc.
4. Save partial progress (links that have been scraped/to be visited) so that I can continue the process.
5. Potential page reuse allocation conflict caused by recursive call after redirection triggered by clicking clickable
6. Saved htmls with a broken format, which misled me to think that javascript support failed and that it didn't get the full html, but it DID. Correct approach: directly write `soup.prettify()` to an html.
7. Implement mechanisms to catch and save failed-to-scrape links and the corresponding error to a csv file.
8. Added feature: save json files that include both page content and the source url.

### Minor Issues Solved
1. Links processing and parsing (join with absolute, remove query params and fragments)
2. Prevent race condition with an asyncio lock and ensure number of pages is properly capped.
3. When saving progress on interruption, add links that are currently being visited (but are in neither self.links nor self.to_visit) back to self.to_visit, as the soupsmaker has not finished scraping those links.


## Retrival-Augmented Generation (RAG)
### Steps
Example implementation: https://docs.langchain.com/oss/python/langchain/rag
1. Split data with langchain splitters and create `Document` objects
#### Plan A: Split text docs using recursive text splitter
Advantage: it attempts to keep paragraphs intact. For example, if a paragraph (or sentence) exceeds chunk size limit, it's moved to the next chunk.
https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter

#### Plan B: Split html docs using HTML splitter
Downside: notion's html pages have too many distracting elements
- HTML loader: take html file and generate a list of `Document` objects of (unsplitted) htmls. https://docs.langchain.com/oss/python/integrations/document_loaders/bshtml
- HTML spliter: take html strings and generate `Document` objects of splitted html segments. https://docs.langchain.com/oss/python/integrations/splitters/split_html

2. Embed with OpenAI and store `.sqlite3` with Chroma
Vector store: 
https://docs.langchain.com/oss/python/integrations/vectorstores/chroma

3. Similarity search directly with vector store. See link in step 2.

4. Implement the agent
- Quick start: https://docs.langchain.com/oss/python/langchain/quickstart
- LangGraph: Sessions memory/storage so that the messages and context are saved: 
https://docs.langchain.com/oss/python/langchain/short-term-memory
https://docs.langchain.com/oss/python/langgraph/persistence
- Configure system prompt, response schema
- Feed retrieved similar docs to "assistant" role in messages when invoking the agent.
- More: see "Issues Solved".

### Issues Solved
1. Integrate tool call limit middleware: https://docs.langchain.com/oss/python/langchain/middleware/built-in#tool-call-limit
2. Provide large overall context to the LLM (scrap key sites that introduce the org, FINCH mission, and team roles) as part of system prompt.
3. Add agent streaming mode for live updates / debugging. For agent streaming: https://docs.langchain.com/oss/python/langchain/streaming.
4. Prevent the agent from exploiting the tool when unnecessary (e.g. retrieve context even if the user's prompt is just 'how are you').
- Current approach: use a third-party LLM judge (that is not biased towards using the tool) for decision making and switch between agent with tool and agent without tool (that shares the same checkpointer), rather than putting the tool to the agent's toolbox and let it decide on its own.
- Memory sharing and thread_ids: The third-party agent should share the same checkpointer memory as the main RAG agent, but they cannot share the same thread_id. Otherwise, conflict arises in the generation process, since graph state of two agents are mixed (e.g. the output of the main agent somehow becomes the output of the third-party helper agent).
5. Adjust embedding chunk size and retrieval k value, referencing some research papers' findings. Prevent the model from exceeding rate limit.
6. Solve chatbot empty final message issue (due to incompatible response schema with the print statements).
7. Add sources for the agent: modify the web scraper to save json files, and modify the response format of the RAG agent to include sources.
8. MOST IMPORTANT: Agent keeps calling the tool, despite the tool limit middleware. This stops the agent from generating a message. The tool can be called hundreds of times. 
- I did not realize this until I streamed all updates. I used to think it was purely due to the latency of running LLM locally. After I found out, I switched from chatgpt-5-nano to chatgpt-4o, and the issue lessened a lot.
- However, the issue is not fully gone. First, sometimes, it still calls the tool a lot, potentially because the model is switched down to a different version due to unknown API limits. Second, chatgpt-4o has much smaller rate limit, so sometimes the input exceeds that.
- Example log: agent with chatgpt-5-nano model called the tool 134 times despite the tool call limit middleware.
```step: ToolCallLimitMiddleware[_retrieve_context].after_model
chunk data: {'thread_tool_call_count': {'_retrieve_context': 1}, 'run_tool_call_count': {'_retrieve_context': 134}, 'messages': [ToolMessage(content="Tool call limit exceeded. Do not call '_retrieve_context' again.", name='_retrieve_context', id='6b897908-80f9-48e1-87e6-0c96ba8390ef', tool_call_id='call_orwEWjS5uccr1urG32K9mxTu', status='error')]}
```
## Packaging into Product: Quick demo -> later web app
### Short-term demo
1. Requirements
- Quick to build
- Cloud deployable
- Basic UI support
2. Library
- Gradio: 
Build a chatbot: https://www.gradio.app/guides/creating-a-chatbot-fast
Display intermediate thoughts and tool usage: https://www.gradio.app/guides/agents-and-tool-usage


### Issues solved
1. Token streaming visuals
2. Markdown string rendering problem: use str.join to better preprocess the response string, which prevents Gradio from misinterpreting inproper indentation as code blocks.

## Next Steps
### For RAG
#### Optional Improvements
1. Add feature: decide dynamically retrieval k value and tool call limit based on necessity score produced by the third-party judge. Must move `create_agent` into the chat loop and create new agents in real time that shares the same checkpointer, since `create_agent` returns `CompiledGraphState` object, which cannot be naively mutated.
2. Two ways of improving retrieval in RAG: https://www.youtube.com/watch?v=smGbeghV1JE.
Idea: LLM-augmented retrieval
- Structured the query with LLM before search
- Restructured the text database with an LLM (e.g. to highlight key info)
3. Prevent sequential context retrieval overlapping. 
- Idea: Filter with document ids with native Chroma API: https://cookbook.chromadb.dev/core/filters.
- Limitation: May need to rewrite the entire embed-store-retrieve pipeline using native Chroma API rather than LangChain Chroma: https://www.datacamp.com/tutorial/chromadb-tutorial-step-by-step-guide
- Attempted using native Chroma in `retrieve_context`, but it cannot recognize the local langchain_chroma persistent database. This shows that we indeed may need to rewrite the entire pipeline using native Chroma if we really want to add this feature.
- Thus, adding this feature might not be worth the time and effort. It doesn't significantly improve the functionality of the chatbot at the end of the day.
4. Add terminal display visuals (e.g. "loading...") - better developer experience.

## Other Links
Scrapers I found online (lack certain features I need):
- RecursiveUrlLoader (not dynamic): https://docs.langchain.com/oss/python/integrations/document_loaders/url
- Dynamic url loader (not recursive): https://docs.langchain.com/oss/python/integrations/document_loaders/recursive_url

Enterprise semantic retriever: Amazon Kendra
https://aws.amazon.com/kendra/features/

Research paper for reference -- "Understanding the Design Decisions of Retrieval-Augmented Generation Systems": https://arxiv.org/html/2411.19463