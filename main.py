from fastapi import FastAPI
from pydantic import BaseModel
from retrieval import CustomRecipeSearcher
import json

CONTENT_INDEX = 'indexes/content'
INGREDIENT_INDEX = 'indexes/ingredients_pretokenized'
INGREDIENT_STATS = 'indexes/stats/ingredients_pretokenized.json'
INGREDIENT_SYNONYMS = 'files/other/synonyms.json'
recipe_path = 'files/raw/foodrecipes_cleaned.json' 
class Search(BaseModel):
    ingredients: str
    keywords: str | None = None
    type: str | None = None
    include_full_recipes: bool = False
    time_range: list[float] | None = None
    serving_size_range: list[float] | None = None
    calories_range: list[float] | None = None

# Initialize the FastAPI app    
app = FastAPI()
# Initialize the search engine and load recipes
engine = CustomRecipeSearcher(CONTENT_INDEX, INGREDIENT_INDEX, INGREDIENT_STATS, synonym_path=INGREDIENT_SYNONYMS)

@app.post("/search/")
async def search(req: Search):
    
    return {"results": [x[0] for x in engine.search(ingredients_str=req.ingredients,
                                        keywords_str=req.keywords, k=10, ranking=req.type,
                                        include_full_recipes=req.include_full_recipes,
                                        cooking_range=req.time_range,
                                        serving_size_range=req.serving_size_range,
                                        calories_range=req.calories_range)]}