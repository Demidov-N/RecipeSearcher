from fastapi import FastAPI
from pydantic import BaseModel
from retrieval import CustomRecipeSearcher

CONTENT_INDEX = 'indexes/content'
INGREDIENT_INDEX = 'indexes/ingredients_pretokenized'
INGREDIENT_STATS = 'indexes/stats/ingredients_pretokenized.json'
INGREDIENT_SYNONYMS = 'files/other/synonyms.json'

class Search(BaseModel):
    ingredients: str
    keywords: str | None = None
    type: str | None = None

app = FastAPI()
engine = CustomRecipeSearcher(CONTENT_INDEX, INGREDIENT_INDEX, INGREDIENT_STATS, synonym_path=INGREDIENT_SYNONYMS)


@app.post("/search/")
async def search(req: Search):
    return {"results": engine.search(ingredients_str=req.ingredients,
                                        keywords_str=req.keywords, k=10, ranking=req.type)}