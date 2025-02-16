from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import httpx
from views import image_view
from database import save_prediction

router = APIRouter(
    prefix="/image",
    tags=["Image Recognition"]
)

@router.post("/recognize")
async def recognize_food(request: Request):
    try:
        content, filename = await image_view.process_image_request(request)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/predict",
                files={'file': (filename, content, 'image/jpeg')}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error from image recognition service"
                )
            
            return await image_view.format_response(response.json())
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/recognize-and-save")
async def recognize_and_save_food(request: Request, user_id: Optional[str] = Header(None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
        
    try:
        content, filename = await image_view.process_image_request(request)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/predict",
                files={'file': (filename, content, 'image/jpeg')}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error from image recognition service"
                )
            
            result = await image_view.format_response(response.json())
            
            main_pred = result["main_prediction"]
            prediction = save_prediction(
                user_id=user_id,
                food_class=main_pred["class"],
                confidence=main_pred["confidence"],
                image_filename=filename
            )
            
            result["prediction_id"] = prediction.id
            return result
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )