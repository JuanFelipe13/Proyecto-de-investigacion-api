from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    IMAGE_RECOGNITION_URL: str = "http://localhost:8001"
    FDC_API_KEY: str = "GRGRljwORxQbtq8DKvamYgOfdHMYbssaWCFVIa5D"  # DEMO_KEY es limitada, registra tu propia key en https://fdc.nal.usda.gov/api-key-signup.html
    
    class Config:
        env_file = ".env"

settings = Settings()