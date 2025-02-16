from fastapi import HTTPException, Request
from typing import Dict, Any, List

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp"
}

async def process_image_request(request: Request) -> tuple[bytes, str]:
    content_type = request.headers.get('content-type', '')
    
    if content_type.startswith('multipart/form-data'):
        form = await request.form()
        file = form.get('file')
        if not file:
            return {
                "status": "error",
                "detail": "No file provided"
            }
        content = await file.read()
        filename = file.filename
    elif content_type in ALLOWED_CONTENT_TYPES:
        content = await request.body()
        extension = ALLOWED_CONTENT_TYPES[content_type]
        filename = f"image.{extension}"
    else:
        return {
            "status": "error",
            "detail": "Invalid content type. Must be JPG, PNG, WebP image or multipart form"
        }
    
    return content, filename

async def format_response(response_data: Dict[str, List[Dict[str, Any]]]):
    if not response_data.get("predictions"):
        return {
            "status": "error",
            "detail": "Invalid response format from prediction service",
            "predictions": []
        }
    
    predictions = response_data["predictions"]
    if not predictions:
        return {
            "status": "error",
            "detail": "No predictions found for this image",
            "predictions": []
        }
    
    sorted_predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)
    
    return {
        "status": "success",
        "main_prediction": sorted_predictions[0],
        "alternative_predictions": sorted_predictions[1:]
    } 