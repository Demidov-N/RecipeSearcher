# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/0.16/topics/item-pipeline.html
from scrapy.exceptions import DropItem
import logging
import pymongo
import hashlib
from datetime import datetime 
from scrapy.utils.project import get_project_settings
import os
import json 

# Get settings
settings = get_project_settings()

# Replace scrapy.log with Python's logging
logger = logging.getLogger(__name__)

class RejectinvalidPipeline(object):
    def process_item(self, item, spider):
        if not item.get('source', False):
            raise DropItem("Missing 'source' in %s" % item)

        if not item.get('title', False):
            raise DropItem("Missing 'title' in %s" % item)

        if not item.get('url', False):
            raise DropItem("Missing 'url' in %s" % item)

        if not item.get('ingredients', False):
            raise DropItem("Missing 'ingredients' in %s" % item)

        return item


class DuplicaterecipePipeline(object):
    """
    This tries to avoid grabbing duplicates within the same session.

    Note that it does not persist between crawls, so it won't reject duplicates
    captured in earlier crawl sessions.
    """

    def __init__(self):
        # initialize ids_seen to empty
        self.ids_seen = set()

    def process_item(self, item, spider):
        # create a string that's just a concatenation of title & url
        # Update string handling for Python 3
        base = "%s%s" % (''.join(item['title']), ''.join(item['url']))
        
        # Update to use encode() with bytes for hashlib
        hash_id = hashlib.md5(base.encode('utf-8')).hexdigest()

        # check if this ID already has been processed
        if hash_id in self.ids_seen:
            #if so, raise this exception that drops (ignores) this item
            raise DropItem("Duplicate title/url: %s" % base)

        else:
            # otherwise add the has to the list of seen IDs
            self.ids_seen.add(hash_id)
            return item


class MongoDBPipeline(object):
    """
    modified from http://snipplr.com/view/65894/
    some ideas from https://github.com/sebdah/scrapy-mongodb/blob/master/scrapy_mongodb.py
    """

    def __init__(self):
        logging.info("Initializing MongoDBPipeline")
        self.uri = settings['MONGODB_URI']
        self.db = settings['MONGODB_DB']
        self.col = settings['MONGODB_COLLECTION']
        
        try:
            # Update MongoClient connection
            logging.info(f"Connecting to MongoDB at {self.uri}")
            connection = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            db = connection[self.db]
            self.collection = db[self.col]

            # Create index
            self.collection.create_index(
                [(settings['MONGODB_UNIQUE_KEY'], pymongo.ASCENDING)],
                unique=True
            )
            
            logging.info('MongoDB connection successful')
            logging.info('Ensuring index for key %s' % settings['MONGODB_UNIQUE_KEY'])
        
        except pymongo.errors.ServerSelectionTimeoutError as err:
            logging.error(f"MongoDB connection error: {err}")
        except Exception as e:
            logging.error(f"Error connecting to MongoDB: {e}")

    def process_item(self, item, spider):
        logging.info("Processing item in MongoDBPipeline")
        try:
            # Convert item to dict
            item_dict = dict(item)
            
            # Add timestamp if configured
            if settings.get('MONGODB_ADD_TIMESTAMP', False):
                item_dict['timestamp'] = datetime.now().isoformat()
            
            # Use replace_one with upsert instead of insert to handle duplicates
            self.collection.replace_one(
                {settings['MONGODB_UNIQUE_KEY']: item_dict.get(settings['MONGODB_UNIQUE_KEY'])},
                item_dict,
                upsert=True
            )
            
            logging.debug(f"Item saved to MongoDB: {item_dict.get('title', 'unnamed')}")
            
        except Exception as e:
            logging.error(f"Error saving item to MongoDB: {e}")
            
        return item

class JsonLinePipeline(object):
    """
    Pipeline to store scraped items in JSONL files.
    Follows the same pattern as MongoDBPipeline.
    """

    def __init__(self):
        logging.info("Initializing JsonLinePipeline")
        self.output_dir = settings.get('JSONL_OUTPUT_DIR', 'output')
        self.filename_prefix = settings.get('JSONL_FILENAME_PREFIX', 'recipes')
        self.file = None
        
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logging.info(f"Created output directory: {self.output_dir}")
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.filename_prefix}_{timestamp}.jsonl"
            self.filepath = os.path.join(self.output_dir, filename)
            
            # Open file for writing
            self.file = open(self.filepath, 'w', encoding='utf-8')
            logging.info(f"JsonLinePipeline initialized. Writing to: {self.filepath}")
            
        except Exception as e:
            logging.error(f"JsonLinePipeline initialization error: {e}")
            self.file = None

    def process_item(self, item, spider):
        if not self.file:
            return item
            
        try:
            # Convert item to dict
            item_dict = dict(item)
            
            # Add timestamp if configured
            if settings.get('JSONL_ADD_TIMESTAMP', True):
                item_dict['_timestamp'] = datetime.now().isoformat()
            
            # Write item as JSON line
            line = json.dumps(item_dict, ensure_ascii=False) + '\n'
            self.file.write(line)
            self.file.flush()  # Ensure immediate writing
            
            logging.debug(f"Item saved to JSONL: {item_dict.get('title', 'unnamed')}")
            
        except Exception as e:
            logging.error(f"Error saving item to JSONL: {e}")
            
        return item
        
    def close_spider(self, spider):
        if self.file:
            self.file.close()
            logging.info(f"JsonLinePipeline closed. File saved at: {self.filepath}")