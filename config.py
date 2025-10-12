import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the Self-Engineering Agent Framework"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Database Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
    
    # Docker Configuration
    DOCKER_IMAGE_NAME = os.getenv("DOCKER_IMAGE_NAME", "self-eng-sandbox")
    DOCKER_TIMEOUT = int(os.getenv("DOCKER_TIMEOUT", "30"))
    
    # Tools Directory
    TOOLS_DIR = os.getenv("TOOLS_DIR", "./tools")
    
    # Flask Configuration
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in environment or .env file")
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set in environment or .env file")
        if not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY must be set in environment or .env file")
        return True


# Validate configuration on import
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"Warning: {e}")

