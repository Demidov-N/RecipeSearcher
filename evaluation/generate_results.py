import json
from re import M
import os, sys

path = os.path.abspath(os.curdir)
# change the current directory 
if path not in sys.path:
    sys.path.append(path)

from retrieval import CustomRecipeSearcher
import pandas as pd
from tqdm import tqdm

# Method to generate results for the search engine
COMBINING_METHOD = 'simple' # or 'rrf'

# Path FROM THE ROOT OF THE PROJECT
QUERRIES_PATH = 'evaluation/querries.csv'
OUTPUT_JSON_PATH = 'evaluation/results.json'
CONTENT_INDEX = 'indexes/content'
INGREDIENT_INDEX = 'indexes/ingredients_pretokenized'
INGREDIENT_STATS = 'indexes/stats/ingredients_pretokenized.json'
INGREDIENT_SYNONYMS = 'files/other/synonyms.json'


def load_queries(querries_path):
    querries = pd.read_csv(querries_path)
    return querries

def generate_results(searcher: CustomRecipeSearcher, querries, n_results=10):
    result_list = []
    for index, row in tqdm(querries.iterrows(), total=len(querries)):
        ingredients = row['ingredients']
        keywords = row['keywords']
        
        if pd.isna(ingredients):
            ingredients = ""
        
        if pd.isna(keywords):
            keywords = ""
        
        result = searcher.search(ingredients_str=ingredients, keywords_str=keywords,
                                 k=n_results, ranking=COMBINING_METHOD)
        result_list.append({
            'ingredients': ingredients,
            'keywords': keywords,
            'results': result
        })
    
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as file:
        json.dump(result_list, file, indent=4)
    print(f"Results saved to {OUTPUT_JSON_PATH}")
    
if __name__ == "__main__":
    # Load the queries
    querries = load_queries(QUERRIES_PATH)
    
    # Initialize the searcher
    searcher = CustomRecipeSearcher(content_path=CONTENT_INDEX,
                                    ingredient_path=INGREDIENT_INDEX,
                                    index_stats_path=INGREDIENT_STATS,
                                    synonym_path=INGREDIENT_SYNONYMS)
    
    # Generate the results
    generate_results(searcher, querries)