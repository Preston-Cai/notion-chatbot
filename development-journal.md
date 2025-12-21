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
6. Saved htmls with a broken format, which misled me to think that javascript support failed and that it didn't get the full html, but it DID. Correct approach: directly write `soup.prettify()` to an html.

### Small issues (solved/unsolved)
1. Links processing and parsing (join with absolute, remove query params and fragments)
2. Avoid creating duplicate tasks (more efficient in resume mode)
3. Prevent race condition with a asyncio lock and ensure number of pages is properly capped.
4. When saving progress on interruption, add links that are currently being visited (but are in neither self.links nor self.to_visit) back to self.to_visit, as the soupsmaker has not finished scraping those links.


## Plans for RAG
1. Split data with langchain splitters and create `Document` objects
#### Plan A: Split text docs using recursive text splitter
Advantage: it attempts to keep paragraphs intact. For example, if a paragraph (or sentence) exceeds chunk size limit, it's moved to the next chunk.
https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter

#### Plan B: Split html docs using HTML splitter
Downside: notion's html pages have too many distracting elements
- HTML loader: take html file and generate a list of `Document` objects of (unsplitted) htmls. https://docs.langchain.com/oss/python/integrations/document_loaders/bshtml
- HTML spliter: take html strings and generate `Document` objects of splitted html segments. https://docs.langchain.com/oss/python/integrations/splitters/split_html

2. Embed with OpenAI and store with Chroma
Vector store: 
https://docs.langchain.com/oss/python/integrations/vectorstores/chroma

3. Similarity search directly with vector store. See link in step 2.


## Other links
Scrapers I found online (lack certain features I need):
- RecursiveUrlLoader (not dynamic): https://docs.langchain.com/oss/python/integrations/document_loaders/url
- Dynamic url loader (not recursive): https://docs.langchain.com/oss/python/integrations/document_loaders/recursive_url


