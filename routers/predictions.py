from fastapi import APIRouter, HTTPException
from typing import List
from models.prediction import Prediction
from database import save_prediction, get_user_predictions, get_prediction, delete_prediction

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)

@router.get("/{user_id}", response_model=List[Prediction])
async def list_predictions(user_id: str):
    result = get_user_predictions(user_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    return result["predictions"]

@router.get("/{user_id}/{prediction_id}", response_model=Prediction)
async def get_prediction_details(user_id: str, prediction_id: str):
    result = get_prediction(prediction_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    
    prediction = result["prediction"]
    if prediction.user_id != user_id:
        raise HTTPException(status_code=404, detail="Prediction not found for this user")
    return prediction

@router.delete("/{user_id}/{prediction_id}")
async def remove_prediction(user_id: str, prediction_id: str):
    result = delete_prediction(user_id, prediction_id)
    if result["status"] == "error":
        raise HTTPException(
            status_code=404 if "not found" in result["detail"] else 403,
            detail=result["detail"]
        )
    return result 