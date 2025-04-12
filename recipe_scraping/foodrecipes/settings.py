# Scrapy settings for thepioneerwoman project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/0.16/topics/settings.html
#

BOT_NAME = 'foodrecipes'

SPIDER_MODULES = ['foodrecipes.spiders']
NEWSPIDER_MODULE = 'foodrecipes.spiders'

ITEM_PIPELINES = {
    'foodrecipes.pipelines.RejectinvalidPipeline': 300,
    'foodrecipes.pipelines.DuplicaterecipePipeline': 500,
    'foodrecipes.pipelines.JsonLinePipeline': 600,
    #'foodrecipes.pipelines.MongoDBPipeline': 700,
}


DOWNLOAD_DELAY = 0.1  # Minimum delay between consecutive requests to the same domain
RANDOMIZE_DOWNLOAD_DELAY = True  # Randomize the download delay to avoid detection
CONCURRENT_REQUESTS_PER_DOMAIN = 16  # Maximum number of concurrent requests that will be performed to any single domain
LOG_LEVEL = 'INFO'

# Request timeouts
DOWNLOAD_TIMEOUT = 60  # Give enough time for slower pages to load

# Auto-throttle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.1  # Initial download delay in seconds
AUTOTHROTTLE_MAX_DELAY = 5      # Maximum download delay in seconds
AUTOTHROTTLE_TARGET_CONCURRENCY = 10.0  # Average number of requests Scrapy should be sending in parallel to each server
AUTOTHROTTLE_DEBUG = False      # Disable showing throttling stats for every response received



# report like a regular browser, but add our info at the end so folks can
# contact us if need be
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31 Open Recipes (+http://openrecip.es)'

# MongoDB stuff in case we want to load it into the database instead of loading it into the separate file
MONGODB_URI = 'mongodb://localhost:27017/'
MONGODB_DB = 'foodrecipes'
MONGODB_COLLECTION = 'recipeitems'
MONGODB_UNIQUE_KEY = 'url'
MONGODB_ADD_TIMESTAMP = True

# Alternatively if does not want to save in MongoDB, save it into file 

# JSONL Pipeline settings
JSONL_OUTPUT_DIR = 'output'  # Directory where JSONL files will be saved
JSONL_FILENAME = 'recipes'   # Base filename (will be appended with timestamp)
JSONL_ADD_TIMESTAMP = True   # Add timestamp to each item

PROXY = 'http://localhost:3128'  # Replace 3128 with your actual Squid proxy port

# Enable the proxy middleware
# Update the middleware format
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}


