from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    IMAGE_RECOGNITION_URL: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"

settings = Settings()