from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import httpx
import os
import logging
from uuid import uuid4
import json
import tempfile
import shutil

from models.nutrition import NutritionData, NutritionSearchResult, ErrorResponse
from services.db_nutrition_service import get_nutrition_data_by_name, get_nutrition_data_by_barcode
from config import settings

router = APIRouter(
    prefix="/nutrition",
    tags=["nutrition"],
    responses={404: {"model": ErrorResponse, "description": "Item not found"}},
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/search/{food_name}", response_model=NutritionSearchResult, summary="Buscar alimento por nombre")
async def search_food_by_name(food_name: str):
    main_result, alternatives = await get_nutrition_data_by_name(food_name)
    
    if not main_result:
        return NutritionSearchResult(
            status="error",
            message=f"No se encontraron datos para: {food_name}",
            data=None,
            alternatives=alternatives
        )
    
    return NutritionSearchResult(
        status="success",
        data=main_result,
        alternatives=alternatives
    )

@router.get("/barcode/{barcode}", response_model=NutritionSearchResult, summary="Buscar alimento por código de barras")
async def search_food_by_barcode(barcode: str):
    result = await get_nutrition_data_by_barcode(barcode)
    
    if not result:
        return NutritionSearchResult(
            status="error",
            message=f"No se encontró producto con código de barras: {barcode}"
        )
    
    return NutritionSearchResult(
        status="success",
        data=result
    )

async def recognize_food_image(image_path: str) -> Dict[str, Any]:
    try:
        image_recognition_url = f"{settings.IMAGE_RECOGNITION_URL}/api/v1/image/predict"
        
        with open(image_path, "rb") as image_file:
            files = {"file": image_file}
            async with httpx.AsyncClient() as client:
                response = await client.post(image_recognition_url, files=files)
            
            if response.status_code != 200:
                logger.error(f"Error en la respuesta del servicio de reconocimiento: {response.text}")
                return {"error": "Error en el servicio de reconocimiento de imágenes"}
            
            result = response.json()
            return result
    
    except Exception as e:
        logger.error(f"Error al reconocer imagen: {str(e)}")
        return {"error": f"Error al procesar la imagen: {str(e)}"}

@router.post("/image", response_model=NutritionSearchResult, summary="Identificar alimento por imagen")
async def identify_food_from_image(file: UploadFile = File(...), user_id: Optional[str] = Form(None)):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid4()}{os.path.splitext(file.filename)[1]}")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        recognition_result = await recognize_food_image(temp_file_path)
        
        if "error" in recognition_result:
            return NutritionSearchResult(
                status="error",
                message=recognition_result["error"]
            )
        
        if "prediction" not in recognition_result or not recognition_result["prediction"]:
            return NutritionSearchResult(
                status="error",
                message="No se pudo identificar ningún alimento en la imagen"
            )
        
        food_class = recognition_result["prediction"]["food_class"]
        confidence = recognition_result["prediction"]["confidence"]
        
        logger.info(f"Alimento identificado: {food_class} (confianza: {confidence})")
        
        main_result, alternatives = await get_nutrition_data_by_name(food_class)
        
        if not main_result:
            return NutritionSearchResult(
                status="partial",
                message=f"Alimento identificado como '{food_class}' (confianza: {confidence:.2f}), pero no se encontraron datos nutricionales",
                alternatives=alternatives
            )
        
        return NutritionSearchResult(
            status="success",
            message=f"Alimento identificado con {confidence:.2f} de confianza",
            data=main_result,
            alternatives=alternatives
        )
        
    except Exception as e:
        logger.error(f"Error al procesar la imagen: {str(e)}")
        return NutritionSearchResult(
            status="error",
            message=f"Error al procesar la imagen: {str(e)}"
        )
    
    finally:
        file.file.close()
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir) 