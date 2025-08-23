# DosyaAI Coolify Deployment Guide

## 🚀 Deployment Steps for DosyaAI Project

### 1. Environment Variables Configuration

Set these environment variables in Coolify for the mcp-mevzuat application:

```bash
# Production Settings
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
WORKERS=2

# Security
SECRET_KEY=your-secret-key-here

# CORS - Specific to Flowise domain
ALLOWED_ORIGINS=https://flowise.software.vision,https://mcp-mevzuat.dosya.ai

# API Configuration
API_TIMEOUT=30.0
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=120
```

### 2. Domain Configuration

**Primary Domain**: `https://mcp-mevzuat.dosya.ai`

**SSL Settings**:
- Enable automatic SSL certificate
- Force HTTPS redirect
- HTTP/2 enabled

### 3. Application Settings

**Repository**: `https://github.com/egeorcun/mevzuat-mcp.git`
**Branch**: `main`
**Build Method**: Dockerfile
**Port**: `8000`

**Health Check**:
- Path: `/health`
- Interval: 30s
- Timeout: 10s
- Retries: 3

### 4. Resource Limits

```yaml
Resources:
  Memory: 512MB
  CPU: 0.5 cores
  
Scaling:
  Min replicas: 1
  Max replicas: 3
  Auto-scale on CPU > 70%
```

### 5. Flowise Integration

**API Base URL**: `https://mcp-mevzuat.dosya.ai`

**Test Endpoints**:
- Health: `GET https://mcp-mevzuat.dosya.ai/health`
- Search: `POST https://mcp-mevzuat.dosya.ai/api/search`

**Example Flowise HTTP Request Node Configuration**:

```json
{
  "method": "POST",
  "url": "https://mcp-mevzuat.dosya.ai/api/search",
  "headers": {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://flowise.software.vision"
  },
  "body": {
    "phrase": "{{$input}}",
    "page_size": 5,
    "sort_field": "RESMI_GAZETE_TARIHI",
    "sort_direction": "desc"
  }
}
```

### 6. Security Considerations

✅ **Implemented Security Measures**:
- CORS restricted to flowise.software.vision only
- HTTPS enforced
- Rate limiting enabled (120 requests/minute)
- Production mode (debug disabled)
- Secure secret key
- Health check monitoring

### 7. Monitoring & Logging

**Log Access**:
- Container logs available in Coolify dashboard
- Application logs: `/app/logs/web_server.log`

**Health Monitoring**:
- Automatic health checks every 30 seconds
- Email alerts on service downtime
- Performance metrics tracking

### 8. Deployment Commands

**Manual Deploy**:
```bash
# In Coolify dashboard
1. Go to DosyaAI project
2. Click "Deploy" button
3. Monitor deployment logs
```

**Auto Deploy**:
- Configured for automatic deployment on git push to main branch
- Webhook URL: `https://coolify.dosya.ai/webhooks/deploy/mcp-mevzuat`

### 9. Testing Deployment

After deployment, test with:

```bash
# Health check
curl https://mcp-mevzuat.dosya.ai/health

# API test
curl -X POST https://mcp-mevzuat.dosya.ai/api/search \
  -H "Content-Type: application/json" \
  -H "Origin: https://flowise.software.vision" \
  -d '{"phrase": "anayasa", "page_size": 2}'
```

### 10. Troubleshooting

**Common Issues**:

1. **CORS Error from Flowise**:
   - Verify ALLOWED_ORIGINS includes flowise.software.vision
   - Check request headers include proper Origin

2. **SSL Certificate Issues**:
   - Ensure DNS points to Coolify server
   - Wait for automatic certificate generation

3. **Container Not Starting**:
   - Check environment variables
   - Review deployment logs in Coolify

4. **API Returns 503**:
   - Service may be starting up (wait 1-2 minutes)
   - Check health endpoint

**Support**:
- Coolify logs: Available in dashboard
- Application logs: Container terminal access
- Health status: `/health` endpoint
