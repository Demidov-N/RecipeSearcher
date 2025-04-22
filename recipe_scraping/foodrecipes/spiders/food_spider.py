from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from recipe_scrapers import scrape_html
import string
food_page_counts = {
  "a": 229,
  "b": 500,
  "c": 893,
  "d": 116,
  "e": 161,
  "f": 188,
  "g": 263,
  "h": 218,
  "i": 76,
  "j": 56,
  "k": 64,
  "l": 194,
  "m": 343,
  "n": 75,
  "o": 122,
  "p": 397,
  "q": 42,
  "r": 199,
  "s": 698,
  "t": 274,
  "u": 20,
  "v": 85,
  "w": 113,
  "x": 2,
  "y": 26,
  "z": 31
}

class FoodnetworkMixin(object):
    source = 'food'

    def parse_item(self, response):
        # skip review pages, which are hard to distinguish from recipe pages
        # in the link extractor regex
        if response.url.endswith('/review'):
            return []

        # Use recipe-scrapers to scrape the recipe
        scraper = scrape_html(response.text, response.url)
        
        # Extract the entire JSON of the scraper
        recipe_data = scraper.to_json()
        recipe_data['source'] = self.source
        recipe_data['url'] = response.url
        
        # Yield the recipe data as an item
        yield recipe_data

class FoodnetworkcrawlSpider(CrawlSpider, FoodnetworkMixin):

    name = "food.com"

    allowed_domains = ["www.food.com", 'food.com']
    
    # generate the start urls from the base url and the list of categories
    

    start_urls = [
        'https://www.food.com/browse/allrecipes/',
    ]
    
    # Generate all possible start URLs programmatically
    def __init__(self, *args, **kwargs):
        super(FoodnetworkcrawlSpider, self).__init__(*args, **kwargs)
        
        # Base URL
        base_url = 'https://www.food.com/browse/allrecipes'
        
        # Generate URLs for all letters (a-z)
        letter_urls = []
        
        letters =  list(string.ascii_lowercase)
        
        # Generate URLs for all pages (1-500) for each letter
        all_urls = []
        for letter in letters:
            start = 1
            max_page = food_page_counts[letter]
            for page in range(start, max_page+1):  # Pages 1-500
                all_urls.append(f"{base_url}?page={page}&letter={letter}")
        
        # Add base URL and letter URLs to the mix
        self.start_urls = [base_url] + letter_urls + all_urls
        #logging.info(f"Generated {len(self.start_urls)} start URLs")

    # Only use rules for recipe pages, not for pagination
    rules = (
        # Rule for recipe pages
        Rule(LinkExtractor(allow=('/recipe/.*')),
             callback='parse_item'),
    )