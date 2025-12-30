from scrapling.fetchers import DynamicFetcher

# Target URL of a dynamic page
url = "https://www.scrapingcourse.com/javascript-rendering"

# Fetch the page and wait for the products to load
page = DynamicFetcher.fetch(
    url,
    wait_selector=".product-link:not([href=''])", # Wait for product nodes to be populated
    headless=True # Run in headless mode
)

# Where to store the scraped data
products = []

# Select all product HTML elements
product_elements = page.css(".product-item")
# Iterate over each product element and apply the scraping logic
for product_element in product_elements:
    name = product_element.css_first(".product-name::text")
    price = product_element.css_first(".product-price::text")
    link = product_element.css_first(".product-link::attr(href)")
    img = product_element.css_first(".product-image::attr(src)")

    # Keep track of the extracted data
    product = {
        "name": name,
        "price": price,
        "url": link,
        "image": img
    }
    products.append(product)

    # For debugging
    print(product)

# Data export logic...