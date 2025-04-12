# Recipe Scraper

This folder contains code and the data that was gathered for the recipe search. The scraper is based on the [OpenRecipes repository](https://github.com/fictive-kin/openrecipes) with adjustments to work with current Python and Scrapy versions.

Additionally, we are using [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) to simplify the scraping process when defining the return output.

## Setup

### Requirements
- Python 3.6+
- MongoDB (optional but recommended)
- Scrapy 2.5+
- Other dependencies listed in `requirements.txt`

### Installation
1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy settings file:
   ```
   cp foodrecipes/settings.py.default foodrecipes/settings.py
   ```
4. Adjust the settings according to your needs

## Configuration

### MongoDB Setup (Preferred Method)
The preferred way to store scraped recipes is in MongoDB, but only if you have database in place

1. Ensure MongoDB is installed and running
2. In your `settings.py`, configure the MongoDB connection:
   ```python
   MONGODB_URI = 'mongodb://username:password@localhost:27017/'
   MONGODB_DB = 'foodrecipes'
   MONGODB_COLLECTION = 'recipeitems'
   MONGODB_UNIQUE_KEY = 'url'
   MONGODB_ADD_TIMESTAMP = True
   ```
   
To use authentication with MongoDB, replace the URI with:
```python
MONGODB_URI = 'mongodb://username:password@localhost:27017/'
```

### File Storage Alternative
If you prefer to store the data in files instead:

1. In your `settings.py`, uncomment the JsonLinePipeline:
   ```python
   ITEM_PIPELINES = {
       'foodrecipes.pipelines.RejectinvalidPipeline': 300,
       'foodrecipes.pipelines.DuplicaterecipePipeline': 500,
       'foodrecipes.pipelines.JsonLinePipeline': 600,  # Uncomment this line
       # 'foodrecipes.pipelines.MongoDBPipeline': 700,  # Comment this line if not using MongoDB
   }
   ```

2. Configure the JSON output settings:
   ```python
   JSONL_OUTPUT_DIR = 'output'
   JSONL_FILENAME = 'recipes'
   JSONL_ADD_TIMESTAMP = True
   ```

### Proxy Settings (Optional)
If you're not using a proxy for caching, remove or comment out these settings:
```python
# PROXY = 'http://localhost:3128'

# DOWNLOADER_MIDDLEWARES = {
#     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
# }
```

## Running the Scraper

For the experiment, we are using the food.com database as it is the most diverse out of all the webpages.

### Basic Execution
```
scrapy crawl food.com
```

### Resumable Crawl
To enable stopping and resuming the crawl:
```
scrapy crawl food.com -s JOBDIR=crawls/food-1
```

You can later stop the process (Ctrl+C) and resume it using the same command.

### Estimated Runtime
The full crawl should take approximately 8 hours to run through all recipes.

## Available Spiders

- `food.com` - Scrapes recipes from Food.com
- `allrecipes.com` - Scrapes recipes from AllRecipes.com

## Output Data Format

Each recipe is stored with the following fields:
- `title` - Recipe title
- `ingredients` - List of ingredients
- `instructions` - Cooking instructions
- `image` - URL to the recipe image
- `url` - Original recipe URL
- `yields` - Number of servings
- `source` - Source website
- And more, depending on what's available on the source page

## Logging

By default, the scraper logs at INFO level. You can adjust the logging level in `settings.py`:
```python
LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## License

This project uses code from OpenRecipes, which is licensed under the MIT License.
