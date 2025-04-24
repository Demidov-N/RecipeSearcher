import os
import csv

import json

from pyserini.analysis import Analyzer, get_lucene_analyzer
from tqdm import tqdm
import shelve

# SETTINGS
GENERATE_SHELF = True
INGREDIENTS_RAW_PATH = 'files/raw/foodrecipes.json'
INGREDIENTS_SHELVES_PATH = 'files/foodrecipes_shelves/foodrecipes_shelves.db'
INGREDIENTS_CLEANED_PATH = 'files/raw/foodrecipes_cleaned.json'
INGREDIENT_INDEX_PATH = 'files/index_jsons/ingredients_pretokenized/ingredients_pretokenized.json'
CONTENT_INDEX_PATH = 'files/index_jsons/content/content.json'
STATS_PATH = 'indexes/stats/ingredients_pretokenized.json'


analyzer = Analyzer(get_lucene_analyzer())

def filter_csv(filename):
    output_rows = []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            if(row[5] != 'Gathered' or 'food.com' not in row[4]):
                continue
            output_rows.append(row)
    with open('trimmed_dataset.csv', 'w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output)
        output.write(',title,ingredients,directions,link,source,NER\n')
        for row in output_rows:
            writer.writerow(row)

#filter_csv('full_dataset.csv')
def build_indices():
    with open('trimmed_dataset.csv', newline='', encoding='utf-8') as f:
        index_source = []
        index_ingredients = []
        index_content = []
        csv_reader = csv.DictReader(f, delimiter=",")
        for row in csv_reader:
            content = row['title'] + '\n' + '\n'.join(json.loads(row['directions']))
            ingredients = json.loads(row['NER'])
            index_source.append({
                'id': row['link'],
                'content': content,
                'content_length': len(analyzer.analyze(content)),
                'ingredients': ingredients,
            })
            index_ingredients.append({
                'id': row['link'],
                'contents': ', '.join(ingredients)
            })
            index_content.append({
                'id': row['link'],
                'contents': content
            })
        with open('ingredients/ingredients.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(index_ingredients))
        with open('content/content.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(index_content))

def build_indices_from_json():
    os.makedirs(os.path.dirname(INGREDIENT_INDEX_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(CONTENT_INDEX_PATH), exist_ok=True)
    with open(INGREDIENTS_CLEANED_PATH, encoding='utf-8') as f:
        recipes = json.load(f)
        index_ingredients = []
        index_content = []
        for i in range(250000):
            if i >= len(recipes):
                break
            recipe = recipes[i]
            ingredients = list(map(lambda x: x.replace(" ", "_"), recipe['ingredients']))
            index_ingredients.append({
                'id': recipe['canonical_url'],
                'contents': ' '.join(ingredients)
            })
            keywords = ' '.join(recipe['keywords']) if 'keywords' in recipe.keys() else " "
            yields =  recipe['yields'] if 'yields' in recipe.keys() else " "
            description = recipe['description'] if 'description' in recipe.keys() else " "
            index_content.append({
                'id': recipe['canonical_url'],
                'contents': '\n'.join([recipe['title'], description, keywords, yields])
            })
        with open(INGREDIENT_INDEX_PATH, 'w+', encoding='utf-8') as file:
            file.write(json.dumps(index_ingredients))
        with open(CONTENT_INDEX_PATH, 'w+', encoding='utf-8') as file:
            file.write(json.dumps(index_content))
            
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def save_recipes_to_shelves(recipes, shelves_path):
    with shelve.open(shelves_path) as shelves:
        for recipe in tqdm(recipes):
            recipe_id = recipe.get('canonical_url')
            recipe_to_insert = {
                'canonical_url': recipe_id,
                'title': recipe.get('title', ''),
                'category': recipe.get('category', ''),
                'description': recipe.get('description', ''),
                'image': recipe.get('image', ''),
                'ingredients': recipe.get('ingredients', []),
                'instructions_list': recipe.get('instructions_list', []),
                'prep_time': recipe.get('prep_time', ''),
                'cook_time': recipe.get('cook_time', ''),
                'ratings': recipe.get('ratings', 0),
                'rating_count': recipe.get('rating_count', 0),
                'total_time': recipe.get('total_time', ''),
                'keywords': recipe.get('keywords', []),
                'calories': recipe.get('nutrients').get('calories', 0) if recipe.get('nutrients') else 0,
                'yields': recipe.get('yields', ''),
                
            }
            if recipe_id is not None:
                shelves[recipe_id] = recipe
                


if __name__ == "__main__":
    if GENERATE_SHELF:
        # Load the JSON data
        recipes = load_json(INGREDIENTS_RAW_PATH)
        
        # Save to shelves
        save_recipes_to_shelves(recipes, INGREDIENTS_SHELVES_PATH)
    
    build_indices_from_json()

#use this code to see index stats
#reader = LuceneIndexReader('indexes/content')
#import itertools
#for term in itertools.islice(reader.terms(), 5):
#    print(f'{term.term} (df={term.df}, cf={term.cf})')

#print(reader.stats())
#print(reader.doc("https://www.food.com/recipe/1-pot-4-item-sausage-suprise-447710").raw())
