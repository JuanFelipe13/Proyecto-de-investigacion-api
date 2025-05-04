import sqlite3
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests
from models.nutrition import NutritionData
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "nutrition.db"

FDC_API_URL = "https://api.nal.usda.gov/fdc/v1"

FDC_API_KEY = settings.FDC_API_KEY

def get_db_connection():
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found: {DB_PATH}")
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    
    return sqlite3.connect(DB_PATH)

def search_local_foods(query: str, limit: int = 25) -> List[Dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_query = f"%{query}%"
        
        cursor.execute('''
            SELECT id, fdc_id, description, brand, serving_size, serving_unit, 
                   food_category, ingredients_text, image_url, origins
            FROM foods 
            WHERE description LIKE ? 
            ORDER BY description ASC
            LIMIT ?
        ''', (search_query, limit))
        
        foods = []
        for row in cursor.fetchall():
            food_id, fdc_id, description, brand, serving_size, serving_unit, \
            food_category, ingredients_text, image_url, origins = row
            
            cursor.execute('''
                SELECT nutrient_type, amount
                FROM nutrients
                WHERE food_id = ?
            ''', (food_id,))
            
            nutrient_rows = cursor.fetchall()
            logger.info(f"Found {len(nutrient_rows)} nutrients for food {description}")
            
            food_nutrients = []
            for nutrient_row in nutrient_rows:
                nutrient_type, amount = nutrient_row
                food_nutrients.append({
                    "nutrientName": nutrient_type,
                    "amount": amount
                })
            
            food = {
                "fdcId": fdc_id,
                "description": description,
                "brandName": brand,
                "servingSize": serving_size,
                "servingSizeUnit": serving_unit,
                "foodCategory": food_category,
                "ingredients": ingredients_text,
                "foodNutrients": food_nutrients,
                "image_url": image_url,
                "origins": origins
            }
            
            foods.append(food)
        
        conn.close()
        logger.info(f"Local search for '{query}': {len(foods)} results found")
        return foods
        
    except Exception as e:
        logger.error(f"Error searching local foods: {str(e)}")
        return []

async def search_fdc_foods(query: str, page_size: int = 25) -> List[Dict]:
    try:
        params = {
            "api_key": FDC_API_KEY,
            "query": query,
            "pageSize": page_size,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"]
        }
        
        response = requests.get(f"{FDC_API_URL}/foods/search", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error in FDC API: {response.status_code} - {response.text}")
            return []
        
        result = response.json()
        return result.get("foods", [])
    
    except Exception as e:
        logger.error(f"Error searching foods in FDC: {str(e)}")
        return []

async def get_food_details(fdc_id: str) -> Optional[Dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, fdc_id, description, brand, serving_size, serving_unit, 
                   food_category, ingredients_text, image_url, origins
            FROM foods 
            WHERE fdc_id = ?
        ''', (fdc_id,))
        
        row = cursor.fetchone()
        if row:
            food_id, fdc_id, description, brand, serving_size, serving_unit, \
            food_category, ingredients_text, image_url, origins = row
            
            cursor.execute('''
                SELECT nutrient_type, amount
                FROM nutrients
                WHERE food_id = ?
            ''', (food_id,))
            
            nutrients = {}
            for nutrient_row in cursor.fetchall():
                nutrient_type, amount = nutrient_row
                nutrients[nutrient_type] = amount
            
            food = {
                "fdcId": fdc_id,
                "description": description,
                "brandName": brand,
                "servingSize": serving_size,
                "servingSizeUnit": serving_unit,
                "foodCategory": food_category,
                "ingredients": ingredients_text,
                "foodNutrients": [{"nutrientName": k, "amount": v} for k, v in nutrients.items()],
                "image_url": image_url,
                "origins": origins
            }
            
            conn.close()
            logger.info(f"Food details for {fdc_id} found in local database")
            return food
            
        conn.close()
        
        logger.info(f"Food details for {fdc_id} not found locally, querying API")
        params = {
            "api_key": FDC_API_KEY,
            "format": "full"
        }
        
        response = requests.get(f"{FDC_API_URL}/food/{fdc_id}", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error getting food details: {response.status_code} - {response.text}")
            return None
        
        food_data = response.json()
        
        if "foodNutrients" not in food_data:
            logger.info(f"API response for {fdc_id} doesn't contain foodNutrients, checking for alternative formats")
            
            if "labelNutrients" in food_data:
                food_data["foodNutrients"] = []
                for nutrient_name, nutrient_data in food_data["labelNutrients"].items():
                    food_data["foodNutrients"].append({
                        "nutrientName": nutrient_name,
                        "amount": nutrient_data.get("value", 0)
                    })
            elif "nutrients" in food_data:
                food_data["foodNutrients"] = []
                for nutrient_name, amount in food_data["nutrients"].items():
                    food_data["foodNutrients"].append({
                        "nutrientName": nutrient_name,
                        "amount": amount
                    })

        if not food_data.get("foodNutrients") and not food_data.get("nutrients"):
            food_data["nutrients"] = {
                "energy": food_data.get("calories", 0),
                "fat": food_data.get("fat", 0),
                "carbohydrates": food_data.get("carbohydrates", 0),
                "proteins": food_data.get("protein", 0),
                "sodium": food_data.get("sodium", 0)
            }
        
        logger.info(f"API response keys for {fdc_id}: {list(food_data.keys())}")
        if "foodNutrients" in food_data:
            logger.info(f"foodNutrients length: {len(food_data['foodNutrients'])}")
        
        return food_data
    
    except Exception as e:
        logger.error(f"Error getting food details: {str(e)}")
        return None

def convert_fdc_food_to_nutrition_data(food_data: Dict) -> NutritionData:
    if not isinstance(food_data, dict):
        logger.error(f"food_data is not a dictionary: {type(food_data)}")
        if isinstance(food_data, str):
            food_data = {"description": food_data}
        else:
            food_data = {"description": "Unknown Food"}
    
    nutrients_dict = {}
    
    if "foodNutrients" in food_data and isinstance(food_data["foodNutrients"], list):
        logger.info(f"Raw foodNutrients data: {food_data['foodNutrients'][:2]}...")
        
        for nutrient in food_data["foodNutrients"]:
            if isinstance(nutrient, dict):
                if "nutrient" in nutrient and isinstance(nutrient["nutrient"], dict):
                    nutrient_info = nutrient["nutrient"]
                    nutrient_id = nutrient_info.get("id")
                    nutrient_name = nutrient_info.get("name", "").lower() if nutrient_info.get("name") else ""
                    amount = nutrient.get("amount") or 0
                elif "number" in nutrient:
                    nutrient_id = nutrient.get("number")
                    nutrient_name = nutrient.get("name", "").lower()
                    amount = nutrient.get("amount") or 0
                else:
                    nutrient_id = nutrient.get("nutrientId") or nutrient.get("id")
                    nutrient_name = nutrient.get("nutrientName", "").lower() or nutrient.get("name", "").lower()
                    amount = nutrient.get("amount") or nutrient.get("value") or 0
                
                if not amount or amount == 0:
                    continue
                
                logger.info(f"Processing nutrient: id={nutrient_id}, name={nutrient_name}, amount={amount}")
                
                if nutrient_name:
                    if ("energy" in nutrient_name or "calorie" in nutrient_name) and not any(key in nutrients_dict for key in ["energy", "calories"]):
                        nutrients_dict["energy"] = float(amount)
                        nutrients_dict["calories"] = float(amount)
                    elif ("fat" in nutrient_name or "lipid" in nutrient_name) and "total" in nutrient_name and "fat" not in nutrients_dict:
                        nutrients_dict["fat"] = float(amount)
                    elif "saturated" in nutrient_name and "fat" in nutrient_name:
                        nutrients_dict["saturated-fat"] = float(amount)
                    elif ("carbohydrate" in nutrient_name or "carbs" in nutrient_name) and "carbohydrates" not in nutrients_dict:
                        nutrients_dict["carbohydrates"] = float(amount)
                    elif "sugar" in nutrient_name and "sugars" not in nutrients_dict:
                        nutrients_dict["sugars"] = float(amount)
                    elif "fiber" in nutrient_name and "fiber" not in nutrients_dict:
                        nutrients_dict["fiber"] = float(amount)
                    elif ("protein" in nutrient_name or "proteins" in nutrient_name) and "proteins" not in nutrients_dict:
                        nutrients_dict["proteins"] = float(amount)
                    elif "sodium" in nutrient_name and "sodium" not in nutrients_dict:
                        nutrients_dict["sodium"] = float(amount)
                        nutrients_dict["salt"] = float(amount) * 2.5
                    elif ("salt" in nutrient_name or "sodium chloride" in nutrient_name) and "salt" not in nutrients_dict:
                        nutrients_dict["salt"] = float(amount)
                        if "sodium" not in nutrients_dict:
                            nutrients_dict["sodium"] = float(amount) / 2.5
    
    if not nutrients_dict and "nutrients" in food_data:
        if isinstance(food_data["nutrients"], dict):
            for key, value in food_data["nutrients"].items():
                if key.lower() in ["energy", "calories", "kcal"]:
                    nutrients_dict["energy"] = float(value)
                    nutrients_dict["calories"] = float(value)
                elif key.lower() in ["fat", "fats", "total fat"]:
                    nutrients_dict["fat"] = float(value)
                elif key.lower() in ["saturated fat", "saturatedfat"]:
                    nutrients_dict["saturated-fat"] = float(value)
                elif key.lower() in ["carbohydrate", "carbohydrates", "carbs"]:
                    nutrients_dict["carbohydrates"] = float(value)
                elif key.lower() in ["sugar", "sugars"]:
                    nutrients_dict["sugars"] = float(value)
                elif key.lower() in ["fiber", "dietary fiber"]:
                    nutrients_dict["fiber"] = float(value)
                elif key.lower() in ["protein", "proteins"]:
                    nutrients_dict["proteins"] = float(value)
                elif key.lower() == "sodium":
                    nutrients_dict["sodium"] = float(value)
                    nutrients_dict["salt"] = float(value) * 2.5
                elif key.lower() == "salt":
                    nutrients_dict["salt"] = float(value)
                    if "sodium" not in nutrients_dict:
                        nutrients_dict["sodium"] = float(value) / 2.5
    
    logger.info(f"Extracted nutrients for {food_data.get('description', 'Unknown')}: {nutrients_dict}")
    
    categories = ""
    if "foodCategory" in food_data:
        if isinstance(food_data["foodCategory"], dict):
            categories = food_data["foodCategory"].get("description", "")
        else:
            categories = str(food_data["foodCategory"])
    elif "food_category" in food_data:
        categories = food_data["food_category"]
    
    serving_size = f"{food_data.get('servingSize', 100)}{food_data.get('servingSizeUnit', 'g')}"
    
    brand = ""
    if "brandName" in food_data:
        brand = food_data["brandName"]
    elif "brand" in food_data:
        brand = food_data["brand"]
    
    return NutritionData(
        food_name=food_data.get("description", "Unknown Food"),
        product_code=str(food_data.get("fdcId", "")),
        brand=brand,
        nutrients=nutrients_dict,
        serving_size=serving_size,
        image_url=food_data.get("image_url", ""),
        ingredients_text=food_data.get("ingredients", ""),
        categories=categories,
        allergens=[],
        origins=food_data.get("origins", "")
    )

async def get_nutrition_data_by_name(food_name: str) -> Tuple[Optional[NutritionData], List[NutritionData]]:
    try:
        logger.info(f"Searching '{food_name}' in local database")
        local_foods = search_local_foods(food_name)
        
        if local_foods:
            logger.info(f"Found {len(local_foods)} local results for '{food_name}'")
            
            main_result = convert_fdc_food_to_nutrition_data(local_foods[0])
            
            alternatives = []
            for food in local_foods[1:5]:
                alternative = convert_fdc_food_to_nutrition_data(food)
                alternatives.append(alternative)
            
            return main_result, alternatives
        
        logger.info(f"No local results for '{food_name}', querying API")
        foods = await search_fdc_foods(food_name)
        
        if not foods:
            logger.warning(f"No results found for: {food_name}")
            return None, []
        
        main_food_details = await get_food_details(str(foods[0].get("fdcId")))
        
        if not main_food_details:
            logger.warning(f"Could not get details for main food: {food_name}")
            return None, []
        
        main_result = convert_fdc_food_to_nutrition_data(main_food_details)
        
        if not main_result.nutrients or len(main_result.nutrients) == 0:
            logger.warning(f"No nutrients found for {main_result.food_name}, using placeholder values")
            main_result.nutrients = {
                "energy": 0,
                "calories": 0,
                "fat": 0,
                "carbohydrates": 0,
                "proteins": 0,
                "sodium": 0,
                "salt": 0
            }
        
        alternatives = []
        for food in foods[1:5]:
            try:
                food_details = await get_food_details(str(food.get("fdcId")))
                if food_details:
                    alternative = convert_fdc_food_to_nutrition_data(food_details)
                    
                    if not alternative.nutrients or len(alternative.nutrients) == 0:
                        alternative.nutrients = {
                            "energy": 0,
                            "calories": 0,
                            "fat": 0,
                            "carbohydrates": 0,
                            "proteins": 0,
                            "sodium": 0,
                            "salt": 0
                        }
                    
                    alternatives.append(alternative)
            except Exception as e:
                logger.error(f"Error processing alternative: {e}")
        
        return main_result, alternatives
        
    except Exception as e:
        logger.error(f"Error searching nutrition data: {e}")
        return None, []

async def get_nutrition_data_by_barcode(barcode: str) -> Optional[NutritionData]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM foods WHERE fdc_id = ?
        ''', (barcode,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            food_details = await get_food_details(barcode)
            if food_details:
                return convert_fdc_food_to_nutrition_data(food_details)
        
        logger.info(f"Querying API for barcode: {barcode}")
        foods = await search_fdc_foods(barcode)
        
        if not foods:
            logger.warning(f"No product found with barcode: {barcode}")
            return None
        
        food_details = await get_food_details(str(foods[0].get("fdcId")))
        
        if not food_details:
            logger.warning(f"Could not get details for barcode: {barcode}")
            return None
        
        return convert_fdc_food_to_nutrition_data(food_details)
        
    except Exception as e:
        logger.error(f"Error searching by barcode: {e}")
        return None 