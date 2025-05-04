from pydantic import BaseModel
from typing import Dict, Optional, List, Any

class NutritionData(BaseModel):
    food_name: str
    product_code: Optional[str] = None
    brand: Optional[str] = None
    nutrients: Dict[str, float] = {}
    serving_size: Optional[str] = None
    image_url: Optional[str] = None
    ingredients_text: Optional[str] = None
    categories: Optional[str] = None
    allergens: Optional[List[str]] = None
    origins: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "food_name": "Apple",
                "product_code": "3175681851624",
                "brand": "Nature's Best",
                "nutrients": {
                    "energy": 52.0,
                    "fat": 0.17,
                    "saturated-fat": 0.03,
                    "carbohydrates": 13.8,
                    "sugars": 10.4,
                    "fiber": 2.4,
                    "proteins": 0.26,
                    "salt": 0.001
                },
                "serving_size": "100g",
                "image_url": "https://images.openfoodfacts.org/product.jpg",
                "ingredients_text": "Apple",
                "categories": "Fruits",
                "allergens": [],
                "origins": "Spain"
            }
        }

class NutritionSearchResult(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[NutritionData] = None
    alternatives: Optional[List[NutritionData]] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Food not found in database"
            }
        } 