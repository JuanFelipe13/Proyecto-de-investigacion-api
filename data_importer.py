import json
import sqlite3
import os
import logging
from database_schema import DB_PATH, create_database
from pathlib import Path
import traceback
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JSON_DATA_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "FoodData_Central_foundation_food_json_2025-04-24.json"

SAMPLE_DATA_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "sample_food_data.json"

def file_exists(path):
    return os.path.exists(path)

def get_data_file_path():
    if file_exists(JSON_DATA_PATH):
        return JSON_DATA_PATH
    elif file_exists(SAMPLE_DATA_PATH):
        logger.warning(f"Main data file not found, using sample data instead: {SAMPLE_DATA_PATH}")
        return SAMPLE_DATA_PATH
    else:
        raise FileNotFoundError(f"Neither main data file nor sample data file found")

NUTRIENT_ID_MAP = {
    "energy": [1008, 2048, 1062],           
    
    "fat": [1004, 1085],                    
    "saturated-fat": [1258],               
    "carbohydrates": [1005, 1050],         
    "proteins": [1003],                     
    "sugars": [1063, 2000],                
    "fiber": [1079, 1082],                  
    
    # Vitamins
    "vitamin-a": [1106],                    
    "vitamin-c": [1162],                    
    "vitamin-d": [1114],                    
    "vitamin-e": [1109],                    
    "vitamin-k": [1185],                    
    "thiamin": [1165],                     
    "riboflavin": [1166],                  
    "niacin": [1167],                      
    "vitamin-b6": [1175],                  
    "folate": [1177],                      
    "vitamin-b12": [1178],                 
    
    # Minerals
    "calcium": [1087],                     
    "iron": [1089],                        
    "magnesium": [1090],                   
    "phosphorus": [1091],                  
    "potassium": [1092],                   
    "sodium": [1093],                      
    "zinc": [1095],                        
    "copper": [1098],                      
    "manganese": [1101],                   
    "selenium": [1103]                     
}

def extract_nutrients_from_fdc(food_nutrients):
    nutrients = {}
    
    for nutrient_item in food_nutrients:
        try:
            if "nutrient" in nutrient_item and isinstance(nutrient_item["nutrient"], dict):
                nutrient_info = nutrient_item["nutrient"]
                nutrient_id = nutrient_info.get("id")
                nutrient_name = nutrient_info.get("name", "").lower() if nutrient_info.get("name") else ""
                amount = nutrient_item.get("amount", 0)
                unit = nutrient_info.get("unitName", "")
                
                if not amount or amount == 0:
                    continue
                
                for our_key, ids in NUTRIENT_ID_MAP.items():
                    if nutrient_id in ids:
                        if unit == "µg" or unit == "mcg":
                            amount = amount * 0.000001  # Convert to grams
                        elif unit == "mg":  # Milligrams
                            amount = amount * 0.001  # Convert to grams
                        
                        nutrients[our_key] = float(amount)
                        break
                
                if nutrient_id == 1062 and "energy" not in nutrients:  
                    nutrients["energy"] = float(amount) * 0.239  
            
            else:
                nutrient_id = nutrient_item.get("nutrientId")
                nutrient_name = nutrient_item.get("nutrientName", "").lower()
                amount = nutrient_item.get("amount") or 0
                
                if not amount or amount == 0:
                    continue
                
                for our_key, ids in NUTRIENT_ID_MAP.items():
                    if nutrient_id in ids:
                        nutrients[our_key] = float(amount)
                        break
                
            if not any(key in nutrients for key in ["energy", "calories"]) and "calorie" in nutrient_name:
                nutrients["energy"] = float(amount)
            elif not "proteins" in nutrients and "protein" in nutrient_name:
                nutrients["proteins"] = float(amount)
            elif not "fat" in nutrients and "total fat" in nutrient_name:
                nutrients["fat"] = float(amount)
            
        except Exception as e:
            continue
    
    if "sodium" in nutrients and "salt" not in nutrients:
        nutrients["salt"] = nutrients["sodium"] * 2.5
    
    return nutrients

def read_jsonl(file_path, max_lines=None):
    foods = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
                
            if line.endswith(','):
                line = line[:-1]
                
            try:
                food = json.loads(line)
                foods.append(food)
                count += 1
                
                if max_lines and count >= max_lines:
                    break
            except json.JSONDecodeError as e:
                logger.warning(f"Error decoding JSON line: {e}. Line: {line[:100]}...")
                continue
    
    return foods

def import_data(clear_existing=True, batch_size=1000, max_foods=None):
    # Create database if it doesn't exist
    create_database()
    
    start_time = time.time()
    
    # Load JSON data
    try:
        data_path = get_data_file_path()
        logger.info(f"Loading data from {data_path}")
        if not os.path.exists(data_path):
            logger.error(f"JSON file not found: {data_path}")
            return False
        
        with open(data_path, 'r', encoding='utf-8') as file:
            first_char = file.read(1)
        
        if first_char == '[':
            with open(data_path, 'r', encoding='utf-8') as file:
                foods = json.load(file)
        else:
            foods = read_jsonl(data_path, max_foods)
        
        food_count = len(foods)
        if max_foods and max_foods < food_count and first_char == '[':
            foods = foods[:max_foods]
            logger.info(f"Limited to {max_foods} foods for testing")
        
        logger.info(f"Loaded {food_count} foods from JSON file")
        
        if food_count == 0:
            logger.warning("No foods loaded from the JSON file")
            return False
            
    except Exception as e:
        logger.error(f"Error loading JSON data: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        if clear_existing:
            logger.info("Clearing existing data...")
            cursor.execute("DELETE FROM nutrients")
            cursor.execute("DELETE FROM allergens")
            cursor.execute("DELETE FROM foods")
            conn.commit()
        
        processed_count = 0
        success_count = 0
        batch_count = 0
        
        conn.execute("BEGIN TRANSACTION")
        
        for food in foods:
            try:
                if not isinstance(food, dict):
                    processed_count += 1
                    continue
                
                fdc_id = str(food.get("fdcId", ""))
                if not fdc_id:
                    processed_count += 1
                    continue
                
                description = food.get("description", "Unknown Food")
                
                food_category = ""
                if "foodCategory" in food:
                    if isinstance(food["foodCategory"], dict):
                        food_category = food["foodCategory"].get("description", "")
                    else:
                        food_category = str(food["foodCategory"])
                
                brand = ""
                if "brandName" in food:
                    brand = food["brandName"]
                elif "brandOwner" in food:
                    brand = food["brandOwner"]
                
                serving_size = food.get("servingSize", 100)
                serving_unit = food.get("servingSizeUnit", "g")
                
                if "foodPortions" in food and isinstance(food["foodPortions"], list) and len(food["foodPortions"]) > 0:
                    for portion in food["foodPortions"]:
                        if isinstance(portion, dict) and "gramWeight" in portion:
                            serving_size = portion.get("gramWeight", 100)
                            if "measureUnit" in portion and isinstance(portion["measureUnit"], dict):
                                measure_unit = portion["measureUnit"].get("name", "")
                                if measure_unit:
                                    serving_unit = measure_unit
                            break
                
                ingredients_text = food.get("ingredients", "")
                if isinstance(ingredients_text, list):
                    ingredients_text = ", ".join(ingredients_text)
                
                if "inputFoods" in food and isinstance(food["inputFoods"], list) and not ingredients_text:
                    input_foods = []
                    for input_food in food["inputFoods"]:
                        if isinstance(input_food, dict):
                            if "foodDescription" in input_food:
                                input_foods.append(input_food["foodDescription"])
                    if input_foods:
                        ingredients_text = ", ".join(input_foods)
                
                logger.info(f"Importing food: {description} (ID: {fdc_id})")
                
                cursor.execute('''
                    INSERT OR REPLACE INTO foods 
                    (fdc_id, description, brand, serving_size, serving_unit, food_category, ingredients_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (fdc_id, description, brand, serving_size, serving_unit, food_category, ingredients_text))
                
                food_id = cursor.lastrowid
                
                if not food_id:
                    processed_count += 1
                    continue
                
                food_nutrients = []
                if "foodNutrients" in food and isinstance(food["foodNutrients"], list):
                    food_nutrients = food["foodNutrients"]
                
                if not food_nutrients:
                    processed_count += 1
                    success_count += 1
                    continue
                
                nutrients = extract_nutrients_from_fdc(food_nutrients)
                
                if nutrients:
                    logger.info(f"Extracted nutrients: {nutrients}")
                
                for nutrient_type, amount in nutrients.items():
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO nutrients
                            (food_id, nutrient_type, amount)
                            VALUES (?, ?, ?)
                        ''', (food_id, nutrient_type, amount))
                    except Exception:
                        continue
                
                success_count += 1
                
                batch_count += 1
                if batch_count >= batch_size:
                    conn.commit()
                    conn.execute("BEGIN TRANSACTION")
                    batch_count = 0
                    elapsed = time.time() - start_time
                    logger.info(f"Processed {processed_count}/{food_count} foods ({success_count} successful) in {elapsed:.1f} seconds")
                
            except Exception as e:
                logger.error(f"Error importing food {food.get('description', 'unknown')}: {str(e)}")
                logger.error(traceback.format_exc())
                processed_count += 1
                continue
            
            processed_count += 1
        
        conn.commit()
        
        elapsed = time.time() - start_time
        logger.info(f"Successfully imported {success_count} of {processed_count} foods in {elapsed:.1f} seconds")

        cursor.execute("SELECT COUNT(*) FROM foods")
        total_foods = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nutrients")
        total_nutrients = cursor.fetchone()[0]
        
        logger.info(f"Database contains {total_foods} foods with {total_nutrients} nutrient entries")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error importing data: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import_data() 