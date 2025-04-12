from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from recipe_scrapers import scrape_html


class ThepioneerwomanMixin(object):

    """
    Using this as a mixin lets us reuse the parse_item method more easily
    """

    # this is the source string we'll store in the DB to aggregate stuff
    # from a single source
    source = 'thepioneerwoman'

    def parse_item(self, response):
        # Use recipe-scrapers to scrape the recipe
        scraper = scrape_html(response.text, response.url)
        
        # Extract the entire JSON of the scraper
        recipe_data = scraper.to_json()
        recipe_data['source'] = self.source
        recipe_data['url'] = response.url
        
        
        # Yield the recipe data as an item
        yield recipe_data


class ThepioneerwomancrawlSpider(CrawlSpider, ThepioneerwomanMixin):

    # this is the name you'll use to run this spider from the CLI
    name = "thepioneerwoman.com"

    # URLs not under this set of domains will be ignored
    allowed_domains = ["thepioneerwoman.com"]

    # the set of URLs the crawler with start with. We're starting on the first
    # page of the site's recipe archive
    start_urls = [
        "http://thepioneerwoman.com/food-cooking/?page=4",
    ]

    # a tuple of Rules that are used to extract links from the HTML page
    rules = (
        # this rule has no callback, so these links will be followed and mined
        # for more URLs. This lets us page through the recipe archives
        Rule(LinkExtractor(allow=('/food-cooking/meals-menus/a\d+/[a-zA-Z-]+/?'))),
        # this rule is for recipe posts themselves. The callback argument will
        # process the HTML on the page, extract the recipe information, and
        # return a RecipeItem object
        Rule(LinkExtractor(allow=('/food-cooking/recipes/a\d+/[a-zA-Z-]+/?')),
             callback='parse_item'),
    )
