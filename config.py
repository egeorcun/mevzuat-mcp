# config.py
"""
Configuration management for Mevzuat MCP Server.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Provides type validation and default values.
    """
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_timeout: float = Field(default=30.0, env="API_TIMEOUT")
    
    # CORS Configuration
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Security
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    
    # Monitoring
    enable_metrics: bool = Field(default=False, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from string."""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def debug(self) -> bool:
        """Enable debug mode in development."""
        return not self.is_production
    
    class Config:
        # Try to load from .env file if it exists
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the current settings instance.
    Useful for dependency injection in FastAPI.
    """
    return settings
