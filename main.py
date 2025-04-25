from fastapi import FastAPI
from pydantic import BaseModel
from retrieval import CustomRecipeSearcher
import json

CONTENT_INDEX = 'indexes/content'
INGREDIENT_INDEX = 'indexes/ingredients_pretokenized'
INGREDIENT_STATS = 'indexes/stats/ingredients_pretokenized.json'
INGREDIENT_SYNONYMS = 'files/other/synonyms.json'
RECIPE_SHELVES_PATH = 'files/foodrecipes_shelves/foodrecipes_shelves.db'

class Search(BaseModel):
    ingredients: str
    keywords: str | None = ""
    type: str | None = "simple"
    include_full_recipes: bool = False
    time_range: list[float] | None = None
    serving_size_range: list[float] | None = None
    calories_range: list[float] | None = None

# Initialize the FastAPI app    
app = FastAPI()
# Initialize the search engine and load recipes
engine = CustomRecipeSearcher(CONTENT_INDEX, INGREDIENT_INDEX, INGREDIENT_STATS, synonym_path=INGREDIENT_SYNONYMS, recipe_path=RECIPE_SHELVES_PATH)

@app.post("/search/")
async def search(req: Search):
    
    return {"results": [x for x in engine.search(ingredients_str=req.ingredients,
                                        keywords_str=req.keywords, k=10, ranking=req.type,
                                        return_full_recipes=req.include_full_recipes,
                                        cooking_range=req.time_range,
                                        serving_size_range=req.serving_size_range,
                                        calories_range=req.calories_range)]}