from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from recipe_scrapers import scrape_html


class AllrecipescrawlSpider(CrawlSpider):
    name = "allrecipes.com"
    allowed_domains = ["allrecipes.com"]
    source = "allrecipes.com"
    
    start_urls = [
        # all of the recipes are linked from this page
        "https://www.allrecipes.com/recipes/",
    ]

    # http://allrecipes.com/recipe/-applesauce-pumpkin-bread/detail.aspx
    # a tuple of Rules that are used to extract links from the HTML page
    rules = (
        # this rule has no callback, so these links will be followed and mined
        # for more URLs. This lets us page through the recipe archives
        Rule(LinkExtractor(allow=('/recipes/ViewAll.aspx\?Page=\d+'))),

        # this rule is for recipe posts themselves. The callback argument will
        # process the HTML on the page, extract the recipe information, and
        # return a RecipeItem object
        Rule(LinkExtractor(allow=('/recipe/.*/detail\.aspx')),
             callback='parse_item'),
    )

    def parse_item(self, response):
        # Use recipe-scrapers to scrape the recipe
        scraper = scrape_html(response.text, response.url)
        
        # Extract the entire JSON of the scraper
        recipe_data = scraper.to_json()
        recipe_data['source'] = self.source
        recipe_data['url'] = response.url
        
        # Yield the recipe data as an item
        yield recipe_data

