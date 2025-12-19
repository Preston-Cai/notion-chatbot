# Development Journal

## Web Scraping

### Tools attempted for scraping notion
1. Basic requests
2. Scrapling dynamic fetcher (customized library on GitHub)
3. Selenium
4. Playwright (finally works)

### Parsing/processing
1. Beautiful Soup

### Algorithms
1. Recursion with constraint (to get all subpages within the base url range)
2. Iterative queue list (to solve recursion limit issue)
3. Async programming (to speed up by opennign multiple tasks): failed due to notion detection.
4. Round robin (to reuse open tabs and avoid overflow)

### Major issues (solved/unsolved):
1. Make sure the page is fully loaded before extracting (sleep + scroll loop)
2. Let the browser stay open (OOP design)
3. Find hidden links through clickables, etc.
4. Save partial progress (links that have been scraped/to be visited) so that I can continue the process.
5. Potential page reuse allocation conflict caused by recursive call after redirection triggered by clicking clickable
6. Saved htmls incorrectly (the format was broken, which misled me to think that javascript support failed and that it didn't get the full html, but it DID). Correct approach: directly write `soup.prettify()` to an html.

### Small issues (solved/unsolved)
1. Links processing and parsing (join with absolute, remove query params and fragments)
2. Avoid creating duplicate tasks (more efficient in resume mode)
3. Prevent race condition with a asyncio lock and ensure number of pages is properly capped.


## Plans for RAG
1. Split html docs using HTML splitter
HTML spliter: generate `Document` objects.
https://docs.langchain.com/oss/python/integrations/splitters/split_html

2. Embed with OpenAI and store with Chroma
Vector store: 
https://docs.langchain.com/oss/python/integrations/vectorstores/chroma

3. Similarity search directly with vector store. See link in step 2.


## Other links
A similar loader to my soupsmaker engine:
https://docs.langchain.com/oss/python/integrations/document_loaders/recursive_url
HTML loader:
https://docs.langchain.com/oss/python/integrations/document_loaders/bshtml
