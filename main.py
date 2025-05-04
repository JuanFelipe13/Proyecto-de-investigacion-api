from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import image, predictions, nutrition

app = FastAPI(
    title="Food Recognition API",
    description="API for food recognition and related services",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(image.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(nutrition.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        reload_dirs=["./"]
    )