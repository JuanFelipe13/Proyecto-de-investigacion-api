from typing import Dict, List, Any
from models.prediction import Prediction
from datetime import datetime
import uuid
from fastapi import HTTPException

# Simulación de base de datos en memoria
predictions_db: Dict[str, Prediction] = {}
user_predictions: Dict[str, List[str]] = {}

def save_prediction(user_id: str, food_class: str, confidence: float, image_filename: str) -> Prediction:
    prediction_id = str(uuid.uuid4())
    prediction = Prediction(
        id=prediction_id,
        user_id=user_id,
        food_class=food_class,
        confidence=confidence,
        image_filename=image_filename,
        created_at=datetime.now()
    )
    predictions_db[prediction_id] = prediction
    
    if user_id not in user_predictions:
        user_predictions[user_id] = []
    user_predictions[user_id].append(prediction_id)
    
    return prediction

def get_user_predictions(user_id: str) -> Dict[str, Any]:
    prediction_ids = user_predictions.get(user_id, [])
    predictions = [predictions_db[pid] for pid in prediction_ids if pid in predictions_db]
    if not predictions:
        return {
            "status": "error",
            "detail": f"No predictions found for user {user_id}",
            "predictions": []
        }
    return {
        "status": "success",
        "predictions": predictions
    }

def get_prediction(prediction_id: str) -> Dict[str, Any]:
    try:
        prediction = predictions_db.get(prediction_id)
        if not prediction:
            return {
                "status": "error",
                "detail": f"Prediction {prediction_id} not found",
                "prediction": None
            }
        return {
            "status": "success",
            "prediction": prediction
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
            "prediction": None
        }

def delete_prediction(user_id: str, prediction_id: str) -> Dict[str, Any]:
    try:
        if prediction_id not in predictions_db:
            return {
                "status": "error",
                "detail": f"Prediction {prediction_id} not found"
            }
        
        if predictions_db[prediction_id].user_id != user_id:
            return {
                "status": "error",
                "detail": "Not authorized to delete this prediction"
            }
        
        del predictions_db[prediction_id]
        user_predictions[user_id].remove(prediction_id)
        return {
            "status": "success",
            "detail": "Prediction deleted successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        } 