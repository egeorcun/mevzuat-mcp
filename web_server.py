# web_server.py
"""
FastAPI web server for Mevzuat API integration with Flowise.
Provides RESTful endpoints that can be consumed by Flowise or other web clients.
"""

import asyncio
import logging
import os
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import configuration
from config import Settings, get_settings

# Import our existing models and client
from mevzuat_client import MevzuatApiClient
from mevzuat_models import (
    MevzuatSearchRequest, MevzuatSearchResult,
    MevzuatTurEnum, SortFieldEnum, SortDirectionEnum,
    MevzuatArticleNode, MevzuatArticleContent,
    MevzuatDocument
)

# Configure logging
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "web_server.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Global client instance
mevzuat_client: Optional[MevzuatApiClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events
    """
    global mevzuat_client
    
    # Startup
    settings = get_settings()
    logger.info("Starting Mevzuat Web API Server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    mevzuat_client = MevzuatApiClient(timeout=settings.api_timeout)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mevzuat Web API Server...")
    if mevzuat_client:
        await mevzuat_client.close()

# Get settings for app configuration
settings = get_settings()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Mevzuat API Server",
    description="RESTful API for Turkish Legislation Search and Content Retrieval",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware for web client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class SearchRequestAPI(BaseModel):
    """
    API request model for searching legislation - simplified for web use
    """
    phrase: Optional[str] = Field(None, description="Full-text search phrase with advanced operators")
    mevzuat_no: Optional[str] = Field(None, description="Specific legislation number")
    resmi_gazete_sayisi: Optional[str] = Field(None, description="Official Gazette issue number")
    mevzuat_turleri: Optional[List[str]] = Field(None, description="List of legislation types to filter by")
    page_number: int = Field(1, ge=1, description="Page number for pagination")
    page_size: int = Field(5, ge=1, le=10, description="Number of results per page")
    sort_field: str = Field("RESMI_GAZETE_TARIHI", description="Field to sort by")
    sort_direction: str = Field("desc", description="Sort direction: 'asc' or 'desc'")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    message: str
    timestamp: str

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    detail: str
    timestamp: str

# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """
    Root endpoint - provides basic API information
    """
    return {
        "service": "Mevzuat API Server",
        "version": "1.0.0",
        "description": "RESTful API for Turkish Legislation Search",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    import datetime
    return HealthResponse(
        status="healthy",
        message="Mevzuat API Server is running",
        timestamp=datetime.datetime.now().isoformat()
    )

@app.post("/api/search", response_model=MevzuatSearchResult)
async def search_legislation(request: SearchRequestAPI):
    """
    Search for Turkish legislation documents
    
    This endpoint provides full-text search capabilities with advanced operators:
    - Boolean operators: AND, OR, NOT
    - Required/prohibited terms: +required -prohibited  
    - Exact phrases: "exact phrase"
    - Proximity search: "word1 word2"~5
    - Wildcard search: word* or w?rd
    - Fuzzy search: word~ or word~0.8
    - Term boosting: important^2
    - Regex patterns: /[a-z]+/
    """
    if not mevzuat_client:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    if not request.phrase and not request.mevzuat_no:
        raise HTTPException(
            status_code=400, 
            detail="At least one search criterion required: 'phrase' or 'mevzuat_no'"
        )
    
    try:
        # Convert API request to internal search request
        search_req = MevzuatSearchRequest(
            phrase=request.phrase,
            mevzuat_no=request.mevzuat_no,
            resmi_gazete_sayisi=request.resmi_gazete_sayisi,
            mevzuat_tur_list=request.mevzuat_turleri or [
                "KANUN", "CB_KARARNAME", "YONETMELIK", "CB_YONETMELIK", 
                "CB_KARAR", "CB_GENELGE", "KHK", "TUZUK", "KKY", "UY", 
                "TEBLIGLER", "MULGA"
            ],
            page_number=request.page_number,
            page_size=request.page_size,
            sort_field=request.sort_field,
            sort_direction=request.sort_direction
        )
        
        logger.info(f"Search request: {request.model_dump(exclude_defaults=True)}")
        
        # Perform search using existing client logic
        result = await mevzuat_client.search_documents(search_req)
        
        logger.info(f"Search completed: {result.total_results} results found")
        
        return result
        
    except Exception as e:
        logger.exception("Error during legislation search")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/legislation/{mevzuat_id}/structure", response_model=List[MevzuatArticleNode])
async def get_legislation_structure(mevzuat_id: str):
    """
    Get the hierarchical structure (table of contents) of a legislation document
    
    Returns the chapters, sections, and articles in a tree structure.
    If empty, the document has no hierarchical structure.
    """
    if not mevzuat_client:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    try:
        logger.info(f"Fetching structure for legislation: {mevzuat_id}")
        
        article_tree = await mevzuat_client.get_article_tree(mevzuat_id)
        
        logger.info(f"Structure fetched: {len(article_tree)} top-level nodes")
        
        return article_tree
        
    except Exception as e:
        logger.exception(f"Error fetching structure for legislation {mevzuat_id}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve structure: {str(e)}")

@app.get("/api/legislation/{mevzuat_id}/content", response_model=MevzuatArticleContent)
async def get_full_legislation_content(mevzuat_id: str):
    """
    Get the full content of a legislation document as markdown
    
    This retrieves the entire document content in one call.
    """
    if not mevzuat_client:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    try:
        logger.info(f"Fetching full content for legislation: {mevzuat_id}")
        
        content = await mevzuat_client.get_full_document_content(mevzuat_id)
        
        if content.error_message:
            raise HTTPException(status_code=404, detail=content.error_message)
            
        logger.info(f"Full content fetched for legislation: {mevzuat_id}")
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching full content for legislation {mevzuat_id}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve content: {str(e)}")

@app.get("/api/legislation/{mevzuat_id}/article/{madde_id}", response_model=MevzuatArticleContent)
async def get_article_content(mevzuat_id: str, madde_id: str):
    """
    Get the content of a specific article within a legislation document
    
    Returns the article content formatted as markdown.
    """
    if not mevzuat_client:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    try:
        logger.info(f"Fetching article content: legislation={mevzuat_id}, article={madde_id}")
        
        content = await mevzuat_client.get_article_content(madde_id, mevzuat_id)
        
        if content.error_message:
            raise HTTPException(status_code=404, detail=content.error_message)
            
        logger.info(f"Article content fetched: legislation={mevzuat_id}, article={madde_id}")
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching article content: legislation={mevzuat_id}, article={madde_id}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve article content: {str(e)}")

@app.get("/api/types", response_model=Dict[str, List[str]])
async def get_legislation_types():
    """
    Get available legislation types for filtering
    """
    return {
        "legislation_types": [
            "KANUN", "CB_KARARNAME", "YONETMELIK", "CB_YONETMELIK", 
            "CB_KARAR", "CB_GENELGE", "KHK", "TUZUK", "KKY", "UY", 
            "TEBLIGLER", "MULGA"
        ],
        "sort_fields": ["RESMI_GAZETE_TARIHI", "KAYIT_TARIHI", "MEVZUAT_NUMARASI"],
        "sort_directions": ["asc", "desc"]
    }

# Custom exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors
    """
    import datetime
    logger.exception("Unhandled exception occurred")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred",
            timestamp=datetime.datetime.now().isoformat()
        ).model_dump()
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from settings
    settings = get_settings()
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    
    uvicorn.run(
        "web_server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,  # Auto-reload in development
        log_level=settings.log_level.lower()
    )
