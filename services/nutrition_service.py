import requests
import json
import os
from typing import Dict, List, Optional, Tuple, Any
import logging
from models.nutrition import NutritionData
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FDC_API_URL = "https://api.nal.usda.gov/fdc/v1"


FDC_API_KEY = settings.FDC_API_KEY

LOCAL_FOOD_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "FoodData_Central_foundation_food_json_2025-04-24.json")

_local_food_data = None

def load_local_food_data() -> List[Dict]:
    global _local_food_data
    if _local_food_data is not None:
        return _local_food_data
    
    try:
        logger.info(f"Cargando datos locales desde {LOCAL_FOOD_DATA_PATH}")
        if os.path.exists(LOCAL_FOOD_DATA_PATH):
            with open(LOCAL_FOOD_DATA_PATH, 'r', encoding='utf-8') as file:
                _local_food_data = json.load(file)
            logger.info(f"Datos locales cargados con éxito: {len(_local_food_data)} alimentos")
            return _local_food_data
        else:
            logger.warning(f"Archivo de datos locales no encontrado: {LOCAL_FOOD_DATA_PATH}")
            _local_food_data = []
            return []
    except Exception as e:
        logger.error(f"Error al cargar datos locales: {str(e)}")
        _local_food_data = []
        return []

def search_local_foods(query: str, limit: int = 25) -> List[Dict]:
    food_data = load_local_food_data()
    
    if not food_data:
        return []
    
    query = query.lower()
    
    matching_foods = []
    for food in food_data:
        if isinstance(food, dict):
            food_name = food.get("description", "").lower()
            if query in food_name:
                matching_foods.append(food)
                if len(matching_foods) >= limit:
                    break
        elif isinstance(food, str):
            food_name = food.lower()
            if query in food_name:
                food_dict = {"description": food}
                matching_foods.append(food_dict)
                if len(matching_foods) >= limit:
                    break
    
    logger.info(f"Búsqueda local para '{query}': {len(matching_foods)} resultados encontrados")
    return matching_foods

def extract_nutrients(nutrients_list: List[Dict]) -> Dict[str, float]:
    # Ver https://fdc.nal.usda.gov/docs/Foundation_Foods_Documentation_Apr2021.pdf para referencia
    nutrient_id_map = {
        "energy": [1008, 2047, 2048, 1062, 2048],      # Tambien Calorías (kcal)
        "fat": [1004, 1085],                
        "saturated-fat": [1258, 1257],       
        "carbohydrates": [1005, 2000, 1050, 1072],        
        "sugars": [2000, 1063, 1074, 1075, 2000],          
        "fiber": [1079, 1082, 1084, 1091, 1085],      
        "proteins": [1003, 1162, 1165, 1168, 1003],         
        "salt": [1093, 1090, 1092, 1093, 1095],               
        "sodium": [1093, 1090, 1092, 1218, 1225]                 
    }
    
    nutrient_name_map = {
        "energy": ["energy", "calories", "kcal", "kilocal"],
        "fat": ["fat", "total fat", "total lipid", "lipids"],
        "saturated-fat": ["saturated", "saturated fat", "saturated fatty acids"],
        "carbohydrates": ["carbohydrate", "carbohydrates", "carbs", "total carbohydrate"],
        "sugars": ["sugar", "sugars", "total sugar", "total sugars"],
        "fiber": ["fiber", "dietary fiber", "total fiber"],
        "proteins": ["protein", "total protein", "proteins"],
        "salt": ["salt", "sodium chloride"],
        "sodium": ["sodium", "na"]
    }
    
    unit_conversion = {
        "g": 1.0,              # gramos
        "mg": 0.001,           # miligramos a gramos
        "µg": 0.000001,        # microgramos a gramos
        "mcg": 0.000001,       # microgramos a gramos
        "kcal": 1.0,           # kilocalorías (para energía)
        "kj": 0.239,           # kilojulios a kilocalorías
        "IU": 0.0,             # Ignoramos unidades internacionales
    }
    
    nutrients = {
        "energy": 0.0,
        "fat": 0.0,
        "saturated-fat": 0.0,
        "carbohydrates": 0.0,
        "sugars": 0.0,
        "fiber": 0.0,
        "proteins": 0.0,
        "salt": 0.0,
        "sodium": 0.0
    }
    
    if not nutrients_list:
        return nutrients
    
    for nutrient in nutrients_list:
        nutrient_id = nutrient.get("nutrientId") or nutrient.get("id")
        nutrient_name = nutrient.get("nutrientName", "").lower() if nutrient.get("nutrientName") else ""
        amount = nutrient.get("amount") or nutrient.get("value") or 0
        unit = (nutrient.get("unitName", "g") or "g").lower()
        
        if amount == 0 or not (nutrient_id or nutrient_name):
            continue
        
        conversion_factor = unit_conversion.get(unit, 1.0)
        amount_converted = float(amount) * conversion_factor
        
        assigned = False
        
        if nutrient_id:
            for nutrient_key, ids in nutrient_id_map.items():
                if nutrient_id in ids:
                    nutrients[nutrient_key] = amount_converted
                    assigned = True
                    break
        
        if not assigned and nutrient_name:
            for nutrient_key, names in nutrient_name_map.items():
                if any(name in nutrient_name for name in names):
                    nutrients[nutrient_key] = amount_converted
                    assigned = True
                    break
    
    if nutrients["sodium"] > 0 and nutrients["salt"] == 0:
        nutrients["salt"] = nutrients["sodium"] * 2.5  # Factor de conversión aproximado
    elif nutrients["salt"] > 0 and nutrients["sodium"] == 0:
        nutrients["sodium"] = nutrients["salt"] / 2.5
    
    return nutrients

async def search_fdc_foods(query: str, page_size: int = 25) -> List[Dict]:
    try:
            
        params = {
            "api_key": FDC_API_KEY,
            "query": query,
            "pageSize": page_size,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],  
        }
        
        response = requests.get(f"{FDC_API_URL}/foods/search", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error en la API de FDC: {response.status_code} - {response.text}")
            return []
        
        result = response.json()
        return result.get("foods", [])
    
    except Exception as e:
        logger.error(f"Error al buscar alimentos en FDC: {str(e)}")
        return []

async def get_food_details(fdc_id: str) -> Optional[Dict]:
    local_data = load_local_food_data()
    for food in local_data:
        if str(food.get("fdcId", "")) == str(fdc_id):
            logger.info(f"Detalles del alimento {fdc_id} encontrados en datos locales")
            return food
    
    try:
        logger.info(f"Consultando API para detalles del alimento {fdc_id}")
        params = {
            "api_key": FDC_API_KEY,
            "format": "full"  
        }
        
        response = requests.get(f"{FDC_API_URL}/food/{fdc_id}", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error al obtener detalles del alimento: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    
    except Exception as e:
        logger.error(f"Error al obtener detalles del alimento: {str(e)}")
        return None

def convert_fdc_food_to_nutrition_data(food_data: Dict) -> NutritionData:
    if not isinstance(food_data, dict):
        logger.error(f"El parámetro food_data no es un diccionario: {type(food_data)}")
        if isinstance(food_data, str):
            food_data = {"description": food_data}
        else:
            food_data = {"description": "Alimento desconocido"}
    
    categories = ""
    if "foodCategory" in food_data:
        if isinstance(food_data["foodCategory"], dict):
            categories = food_data["foodCategory"].get("description", "")
        else:
            categories = str(food_data["foodCategory"])
    elif "foodGroup" in food_data:
        if isinstance(food_data["foodGroup"], dict):
            categories = food_data["foodGroup"].get("description", "")
        else:
            categories = str(food_data["foodGroup"])
    
    ingredients_text = food_data.get("ingredients", "")
    
    brand = ""
    if "brandName" in food_data:
        brand = food_data["brandName"]
    elif "brandOwner" in food_data:
        brand = food_data["brandOwner"]
    
    return NutritionData(
        food_name=food_data.get("description", "Alimento sin nombre"),
        product_code=str(food_data.get("fdcId", "")),
        brand=brand,
        nutrients=extract_nutrients(food_data.get("foodNutrients", [])),
        serving_size=f"{food_data.get('servingSize', 100)}{food_data.get('servingSizeUnit', 'g')}",
        image_url="",  
        ingredients_text=ingredients_text,
        categories=categories,
        allergens=[],  
        origins=""
    )

async def get_nutrition_data_by_name(food_name: str) -> Tuple[Optional[NutritionData], List[NutritionData]]:
    try:
        logger.info(f"Buscando '{food_name}' en datos locales")
        local_foods = search_local_foods(food_name)
        
        if local_foods:
            logger.info(f"Se encontraron {len(local_foods)} resultados locales para '{food_name}'")
            
            main_result = convert_fdc_food_to_nutrition_data(local_foods[0])
            
            alternatives = []
            for food in local_foods[1:5]:  
                alternative_data = convert_fdc_food_to_nutrition_data(food)
                alternatives.append(alternative_data)
            
            return main_result, alternatives
        
        foods = await search_fdc_foods(food_name)
        
        if not foods:
            logger.warning(f"No se encontraron resultados para: {food_name}")
            return None, []
        
        main_food_details = await get_food_details(str(foods[0].get("fdcId")))
        
        if not main_food_details:
            logger.warning(f"No se pudieron obtener detalles para el alimento principal: {food_name}")
            return None, []
        
        main_result = convert_fdc_food_to_nutrition_data(main_food_details)
        
        alternatives = []
        for food in foods[1:5]:  
            try:
                food_details = await get_food_details(str(food.get("fdcId")))
                if food_details:
                    alternative_data = convert_fdc_food_to_nutrition_data(food_details)
                    alternatives.append(alternative_data)
                else:
                    food_category = ""
                    if "foodCategory" in food:
                        if isinstance(food["foodCategory"], dict):
                            food_category = food["foodCategory"].get("description", "")
                        else:
                            food_category = str(food["foodCategory"])
                            
                    alternative_data = NutritionData(
                        food_name=food.get("description", ""),
                        product_code=str(food.get("fdcId", "")),
                        brand=food.get("brandOwner", ""),
                        nutrients=extract_nutrients(food.get("foodNutrients", [])),
                        serving_size=f"{food.get('servingSize', 100)}{food.get('servingSizeUnit', 'g')}",
                        categories=food_category
                    )
                    alternatives.append(alternative_data)
            except Exception as e:
                logger.error(f"Error procesando alternativa: {e}")
        
        return main_result, alternatives
        
    except Exception as e:
        logger.error(f"Error al buscar datos nutricionales: {e}")
        return None, []

async def get_nutrition_data_by_barcode(barcode: str) -> Optional[NutritionData]:
    try:
        local_foods = search_local_foods(barcode)
        if local_foods:
            logger.info(f"Alimento encontrado en datos locales con código de barras: {barcode}")
            return convert_fdc_food_to_nutrition_data(local_foods[0])
            
        logger.info(f"Consultando API para código de barras: {barcode}")
        foods = await search_fdc_foods(barcode)
        
        if not foods:
            logger.warning(f"No se encontró producto con código: {barcode}")
            return None
        
        food_details = await get_food_details(str(foods[0].get("fdcId")))
        
        if not food_details:
            logger.warning(f"No se pudieron obtener detalles para el código: {barcode}")
            return None
        
        return convert_fdc_food_to_nutrition_data(food_details)
        
    except Exception as e:
        logger.error(f"Error al buscar por código: {e}")
        return None 