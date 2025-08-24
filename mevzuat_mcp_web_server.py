"""
Mevzuat MCP Web Server - Turkish Legislation MCP Server

This module provides a comprehensive MCP server for Turkish legislation
with HTTP API support, authentication, and Flowise compatibility.

Features:
- MCP Protocol over HTTP
- Bearer token authentication
- CORS support for Flowise
- Comprehensive logging
- Health checks
- Tool discovery endpoints
"""

import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import our existing client and models
from mevzuat_client import MevzuatApiClient, MevzuatSearchRequest
from mevzuat_models import MevzuatDocument, MevzuatSearchResult, MevzuatArticleNode

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Create logs directory
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "mevzuat_mcp.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Security configuration
API_KEY = os.getenv("MCP_API_KEY", "your-secret-api-key-here")
FLOWISE_ORIGIN = "https://flowise.software.vision"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", FLOWISE_ORIGIN).split(",")

# ============================================================================
# MODELS
# ============================================================================

class MCPRequest(BaseModel):
    """MCP JSON-RPC request model"""
    jsonrpc: str = "2.0"
    id: Union[int, str]
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    """MCP JSON-RPC response model"""
    jsonrpc: str = "2.0"
    id: Union[int, str]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    uptime_seconds: float
    version: str
    tools_count: int
    mcp_endpoint: str

class ServerInfo(BaseModel):
    """Server information model"""
    name: str
    version: str
    description: str
    tools_count: int
    mcp_endpoint: str
    api_docs: str

# ============================================================================
# MCP TOOLS DEFINITION
# ============================================================================

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

# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================

# Initialize Mevzuat API client
mevzuat_client = MevzuatApiClient()

# ============================================================================
# AUTHENTICATION
# ============================================================================

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

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
    
    # Check origin (allow Flowise or None for MCP clients)
    if origin and origin != FLOWISE_ORIGIN:
        logger.warning(f"Unauthorized origin attempt: {origin}")
        raise HTTPException(
            status_code=403,
            detail="Unauthorized origin"
        )
    
    logger.info(f"Authenticated request from: {origin or 'MCP Client'}")
    return True

# ============================================================================
# LIFECYCLE MANAGEMENT
# ============================================================================

SERVER_START_TIME = datetime.now()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Mevzuat MCP Web Server...")
    logger.info(f"Environment: {'development' if DEBUG else 'production'}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'your-secret-api-key-here' else 'No'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mevzuat MCP Web Server...")

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Mevzuat MCP Web Server",
    description="""
    Turkish Legislation MCP Server with HTTP API support.
    
    This server provides access to Turkish legislation through:
    • Mevzuat.gov.tr API integration
    • MCP Protocol over HTTP
    • Flowise compatibility
    • Bearer token authentication
    
    Available tools:
    • search_documents - Search Turkish legislation
    • get_article_tree - Get legislation table of contents
    • get_article_content - Get specific article content
    • get_document_content - Get full legislation content
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for web client access - only allow Flowise
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "message": "Mevzuat MCP Web Server",
        "version": "1.0.0",
        "description": "Turkish Legislation MCP Server",
        "endpoints": {
            "mcp": "POST /mcp - MCP Protocol endpoint",
            "tools": "GET /mcp/tools - List available tools",
            "actions": "GET /mcp/actions - List available actions (Flowise)",
            "health": "GET /health - Health check",
            "docs": "GET /docs - API documentation"
        },
        "secure": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    uptime = (datetime.now() - SERVER_START_TIME).total_seconds()
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        uptime_seconds=uptime,
        version="1.0.0",
        tools_count=len(MCP_TOOLS),
        mcp_endpoint="/mcp"
    )

@app.get("/mcp")
async def mcp_get_endpoint():
    """GET endpoint for MCP - returns basic info"""
    return {
        "message": "Mevzuat MCP Web Server",
        "version": "1.0.0",
        "protocol": "MCP",
        "endpoint": "POST /mcp for MCP requests",
        "tools_count": len(MCP_TOOLS),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/mcp/tools")
async def list_tools_endpoint():
    """GET endpoint to list all available MCP tools"""
    tools = []
    for tool_name, tool_def in MCP_TOOLS.items():
        tools.append({
            "name": tool_def["name"],
            "description": tool_def["description"],
            "inputSchema": tool_def["inputSchema"]
        })
    
    return {
        "message": "Available MCP Tools",
        "count": len(tools),
        "tools": tools
    }

@app.get("/mcp/actions")
async def list_actions_endpoint():
    """GET endpoint for Flowise to list available actions"""
    actions = []
    for tool_name, tool_def in MCP_TOOLS.items():
        actions.append({
            "label": tool_def["description"],
            "name": tool_def["name"],
            "type": "string",
            "required": True,
            "description": tool_def["description"]
        })
    
    return actions

@app.get("/mcp/flowise-actions")
async def flowise_actions_endpoint():
    """Special endpoint for Flowise Custom MCP Tool"""
    actions = []
    for tool_name, tool_def in MCP_TOOLS.items():
        actions.append({
            "label": tool_def["description"],
            "name": tool_def["name"],
            "type": "string",
            "required": True,
            "description": tool_def["description"],
            "inputSchema": tool_def["inputSchema"]
        })
    
    return {
        "actions": actions,
        "count": len(actions),
        "server": "Mevzuat MCP",
        "version": "1.0.0"
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
            result = await handle_list_tools(mcp_request)
            logger.info(f"Tools list response: {len(result.result.get('tools', []))} tools")
            return result
        elif mcp_request.method == "listActions":
            result = await handle_list_actions(mcp_request)
            logger.info(f"ListActions response: {len(result.result.get('actions', []))} actions")
            return result
        elif mcp_request.method == "tools/call":
            return await handle_call_tool(mcp_request)
        elif mcp_request.method == "initialize":
            result = await handle_initialize(mcp_request)
            logger.info("Initialize response sent")
            return result
        else:
            logger.warning(f"Unknown method: {mcp_request.method}")
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

# ============================================================================
# MCP HANDLERS
# ============================================================================

async def handle_initialize(request: MCPRequest) -> MCPResponse:
    """Handle MCP initialize request"""
    return MCPResponse(
        id=request.id,
        result={
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                }
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

async def handle_list_actions(request: MCPRequest) -> MCPResponse:
    """Handle Flowise listActions request"""
    try:
        actions = []
        for tool_name, tool_def in MCP_TOOLS.items():
            actions.append({
                "label": tool_def["description"],
                "name": tool_def["name"],
                "type": "string",
                "required": True,
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"]
            })
        
        logger.info(f"Returning {len(actions)} actions for Flowise")
        return MCPResponse(
            id=request.id,
            result={
                "actions": actions,
                "count": len(actions),
                "server": "Mevzuat MCP",
                "version": "1.0.0"
            }
        )
    except Exception as e:
        logger.error(f"Error listing actions: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": str(e)
            }
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

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

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
        return {"content": result}
        
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
        return {"content": result}
        
    except Exception as e:
        logger.error(f"Error in get_document_content_tool: {e}")
        return {"error": str(e)}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Mevzuat MCP Web Server...")
    logger.info(f"Environment: {'development' if DEBUG else 'production'}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'your-secret-api-key-here' else 'No'}")
    
    uvicorn.run(
        "mevzuat_mcp_web_server:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )
