# mevzuat_mcp_web_server.py
"""
Web MCP Server for Mevzuat API - exposes MCP protocol over HTTP
Similar to yargi-mcp implementation for Flowise integration
"""

import asyncio
import logging
import os
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "mcp_web_server.log")
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

# Security configuration
API_KEY = os.getenv("MCP_API_KEY", "your-secret-api-key-here")
FLOWISE_ORIGIN = "https://flowise.software.vision"

# HTTP Bearer token security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events
    """
    global mevzuat_client
    
    # Startup
    settings = get_settings()
    logger.info("Starting Mevzuat MCP Web Server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'your-secret-api-key-here' else 'No (using default)'}")
    
    mevzuat_client = MevzuatApiClient(timeout=settings.api_timeout)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mevzuat MCP Web Server...")
    if mevzuat_client:
        await mevzuat_client.close()

# Get settings for app configuration
settings = get_settings()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Mevzuat MCP Web Server",
    description="Web MCP Server for Turkish Legislation Search and Content Retrieval",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware for web client access - only allow Flowise
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FLOWISE_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security dependency
async def verify_api_key(
    authorization: HTTPAuthorizationCredentials = Depends(security),
    origin: Optional[str] = Header(None)
) -> bool:
    """
    Verify API key and origin for security
    """
    # Check API key
    if authorization.credentials != API_KEY:
        logger.warning(f"Invalid API key attempt from origin: {origin}")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Check origin (only allow Flowise)
    if origin != FLOWISE_ORIGIN:
        logger.warning(f"Unauthorized origin attempt: {origin}")
        raise HTTPException(
            status_code=403,
            detail="Unauthorized origin"
        )
    
    logger.info(f"Authenticated request from: {origin}")
    return True

# MCP Protocol Models
class MCPRequest(BaseModel):
    """Base MCP request model"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    """Base MCP response model"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

# MCP Tool Definitions
MCP_TOOLS = {
    "search_documents": {
        "name": "search_documents",
        "description": "Searches for Turkish legislation on mevzuat.gov.tr",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phrase": {
                    "type": "string",
                    "description": "Turkish full-text search phrase"
                },
                "mevzuat_no": {
                    "type": "string",
                    "description": "The specific number of the legislation"
                },
                "page_number": {
                    "type": "integer",
                    "default": 1,
                    "description": "Page number for pagination"
                },
                "page_size": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return per page"
                }
            },
            "required": []
        }
    },
    "get_article_tree": {
        "name": "get_article_tree",
        "description": "Retrieves the table of contents for a specific legislation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "The ID of the legislation"
                }
            },
            "required": ["mevzuat_id"]
        }
    },
    "get_article_content": {
        "name": "get_article_content",
        "description": "Retrieves the content of a specific article",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "The ID of the legislation"
                },
                "madde_id": {
                    "type": "string",
                    "description": "The ID of the specific article"
                }
            },
            "required": ["mevzuat_id", "madde_id"]
        }
    },
    "get_document_content": {
        "name": "get_document_content",
        "description": "Retrieves the full content of a legislation document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "The ID of the legislation"
                }
            },
            "required": ["mevzuat_id"]
        }
    }
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Mevzuat MCP Web Server", "version": "1.0.0", "secure": True}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Mevzuat MCP Web Server is running",
        "secure": True,
        "timestamp": asyncio.get_event_loop().time()
    }

@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Main MCP endpoint that handles all MCP protocol requests
    Requires API key authentication and Flowise origin
    """
    try:
        # Parse the request body
        body = await request.json()
        mcp_request = MCPRequest(**body)
        
        logger.info(f"Authenticated MCP Request: {mcp_request.method}")
        
        # Handle different MCP methods
        if mcp_request.method == "tools/list":
            return await handle_list_tools(mcp_request)
        elif mcp_request.method == "tools/call":
            return await handle_call_tool(mcp_request)
        elif mcp_request.method == "initialize":
            return await handle_initialize(mcp_request)
        else:
            return MCPResponse(
                id=mcp_request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {mcp_request.method}"
                }
            )
            
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return MCPResponse(
            id=body.get("id") if 'body' in locals() else None,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )

async def handle_initialize(request: MCPRequest) -> MCPResponse:
    """Handle MCP initialize request"""
    return MCPResponse(
        id=request.id,
        result={
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "MevzuatGovTrMCP",
                "version": "1.0.0"
            }
        }
    )

async def handle_list_tools(request: MCPRequest) -> MCPResponse:
    """Handle MCP tools/list request"""
    tools = []
    for tool_name, tool_def in MCP_TOOLS.items():
        tools.append({
            "name": tool_def["name"],
            "description": tool_def["description"],
            "inputSchema": tool_def["inputSchema"]
        })
    
    return MCPResponse(
        id=request.id,
        result={"tools": tools}
    )

async def handle_call_tool(request: MCPRequest) -> MCPResponse:
    """Handle MCP tools/call request"""
    if not request.params:
        return MCPResponse(
            id=request.id,
            error={"code": -32602, "message": "Invalid params"}
        )
    
    tool_name = request.params.get("name")
    arguments = request.params.get("arguments", {})
    
    if tool_name not in MCP_TOOLS:
        return MCPResponse(
            id=request.id,
            error={"code": -32601, "message": f"Tool not found: {tool_name}"}
        )
    
    try:
        # Call the appropriate tool
        if tool_name == "search_documents":
            result = await search_documents_tool(arguments)
        elif tool_name == "get_article_tree":
            result = await get_article_tree_tool(arguments)
        elif tool_name == "get_article_content":
            result = await get_article_content_tool(arguments)
        elif tool_name == "get_document_content":
            result = await get_document_content_tool(arguments)
        else:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Tool not implemented: {tool_name}"}
            )
        
        return MCPResponse(
            id=request.id,
            result={"content": result}
        )
        
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            }
        )

# Tool implementations
async def search_documents_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of search_documents tool"""
    try:
        # Create search request
        search_request = MevzuatSearchRequest(
            phrase=arguments.get("phrase"),
            mevzuat_no=arguments.get("mevzuat_no"),
            page_number=arguments.get("page_number", 1),
            page_size=arguments.get("page_size", 5)
        )
        
        # Perform search
        result = await mevzuat_client.search_documents(search_request)
        
        # Convert to dict
        return {
            "documents": [doc.model_dump() for doc in result.documents],
            "total_results": result.total_results,
            "current_page": result.current_page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "error_message": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error in search_documents_tool: {e}")
        return {"error": str(e)}

async def get_article_tree_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of get_article_tree tool"""
    try:
        mevzuat_id = arguments.get("mevzuat_id")
        if not mevzuat_id:
            return {"error": "mevzuat_id is required"}
        
        result = await mevzuat_client.get_article_tree(mevzuat_id)
        return {"nodes": [node.model_dump() for node in result]}
        
    except Exception as e:
        logger.error(f"Error in get_article_tree_tool: {e}")
        return {"error": str(e)}

async def get_article_content_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of get_article_content tool"""
    try:
        mevzuat_id = arguments.get("mevzuat_id")
        madde_id = arguments.get("madde_id")
        
        if not mevzuat_id or not madde_id:
            return {"error": "mevzuat_id and madde_id are required"}
        
        result = await mevzuat_client.get_article_content(mevzuat_id, madde_id)
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Error in get_article_content_tool: {e}")
        return {"error": str(e)}

async def get_document_content_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Implementation of get_document_content tool"""
    try:
        mevzuat_id = arguments.get("mevzuat_id")
        if not mevzuat_id:
            return {"error": "mevzuat_id is required"}
        
        result = await mevzuat_client.get_document_content(mevzuat_id)
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Error in get_document_content_tool: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
