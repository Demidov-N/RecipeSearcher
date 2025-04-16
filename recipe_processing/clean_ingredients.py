import json
from tqdm.auto import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import spacy

# Import your parser function.
from ingredient_parser import parse_ingredient


FOODRECIPES_RAW = 'files/raw/foodrecipes.json'
FOODRECIPES_CLEAN = 'files/raw/foodrecipes_cleaned.json'

# Global variable to hold the spaCy model for each worker
nlp = None

def init_worker():
    """
    This initializer is run once per process when the pool starts.
    It loads the spaCy model into the global variable.
    """
    global nlp
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])


def process_recipe(recipe):
    """
    Process one recipe:
      - Lowercase, lemmatize, and parse each ingredient string with parse_ingredient.
      - Extract the ingredient name from the parsed result.
      - Build a new dictionary retaining only title, keywords, yields, description, and processed ingredients.
    """
    global nlp
    new_recipe = {
        "title": recipe.get("title", ""),
        'canonical_url': recipe.get("canonical_url", ""),
        "keywords": recipe.get("keywords", []),
        "yields": recipe.get("yields", ""),
        "description": recipe.get("description", "")
    }
    
    raw_ingredients = recipe.get("ingredients", [])
    processed_ingredients = []
    
    for ing in raw_ingredients:
        # Lowercase and strip extra whitespace.
        parsed = parse_ingredient(ing)
        if hasattr(parsed, "name") and isinstance(parsed.name, list) and parsed.name:
            for name in parsed.name:
                lemmatized_ing = ""
                if hasattr(name, "text"):
                    ing = name.text.strip()
                    lemmatized_ing = " ".join([token.lemma_.lower() for token in nlp(ing) if not token.is_stop and not token.is_punct])
                processed_ingredients.append(lemmatized_ing)
    
    new_recipe["ingredients"] = processed_ingredients
    return new_recipe

def main():
    # Load recipes from input JSON.
    with open(FOODRECIPES_RAW, "r", encoding="UTF-8") as f:
        print("Loading recipes...")
        recipes = json.load(f)
        print("Recipes loaded, preparing for processing...")
    new_recipes = []
    
    # Create a ProcessPoolExecutor with, for example, 4 workers.
    with ProcessPoolExecutor(max_workers=8, initializer=init_worker) as executor:
        # Submit each recipe for processing.
        print("Preparing futures")
        futures = [executor.submit(process_recipe, recipe) for recipe in tqdm(recipes, desc="Submitting recipes")]  
        print("Showing progress bar")
        # Use tqdm to track progress.
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing recipes"):
            try:
                new_recipe = future.result()
                new_recipes.append(new_recipe)
            except Exception as e:
                print("Error processing a recipe:", e)
    
    # Save the new JSON output.
    with open(FOODRECIPES_CLEAN, "w") as f:
        json.dump(new_recipes, f, indent=2)
    
    print("Processing complete! Processed recipes saved to 'processed_recipes_parallel.json'.")

if __name__ == "__main__":
    main()