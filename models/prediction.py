from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PredictionCreate(BaseModel):
    user_id: str
    food_class: str
    confidence: float
    image_filename: str

class Prediction(PredictionCreate):
    id: str
    created_at: datetime 