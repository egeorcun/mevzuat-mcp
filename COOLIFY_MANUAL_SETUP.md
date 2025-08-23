# Manual Coolify Setup for mcp-mevzuat.dosya.ai

## 🚀 Step-by-Step Deployment Guide

Bu dosya, Coolify dashboard'u üzerinden manual olarak `mcp-mevzuat.dosya.ai` domain'i için deployment yapmak için gerekli tüm ayarları içerir.

### 1. New Application Creation

**Coolify Dashboard Steps:**

1. **Project**: `dosyaai` seçin
2. **Environment**: `production` seçin  
3. **Server**: `Remote Server with Cloudflare Tunneled` seçin
4. **Source Type**: `GitHub`
5. **Repository**: `egeorcun/mevzuat-mcp`
6. **Branch**: `main`

### 2. Application Configuration

**Build Settings:**
```
Build Pack: Dockerfile
Dockerfile Location: /Dockerfile
Base Directory: /
Build Command: (empty)
Install Command: (empty)
Start Command: (empty) - will use Dockerfile CMD
```

**Port Configuration:**
```
Ports Exposed: 8000
```

**Health Check:**
```
Enabled: ✅
Path: /health
Method: GET
Port: 8000
Interval: 30s
Timeout: 10s
Retries: 3
Start Period: 30s
```

### 3. Environment Variables

**Core Application Settings:**
```bash
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
WORKERS=2
```

**Security & Authentication:**
```bash
SECRET_KEY=gviG6vChjyUhhTwkYYTRlTVb1nPMzTwgxz0-xX53BMI
```

**CORS Configuration:**
```bash
ALLOWED_ORIGINS=https://flowise.software.vision,https://mcp-mevzuat.dosya.ai
```

**API Configuration:**
```bash
API_TIMEOUT=30.0
LOG_LEVEL=INFO
```

**Rate Limiting:**
```bash
RATE_LIMIT_PER_MINUTE=120
```

### 4. Domain Configuration

**Domain Setup:**
1. Go to **Domains** tab in application
2. Click **+ Add Domain**
3. Enter: `mcp-mevzuat.dosya.ai`
4. **SSL**: Enable automatic Let's Encrypt
5. **Force HTTPS**: Enable
6. **WWW Redirect**: Disable

**DNS Configuration:**
- Ensure `mcp-mevzuat.dosya.ai` A record points to Cloudflare Tunnel IP
- TTL: 300 seconds

### 5. Resource Limits

**Container Resources:**
```yaml
Memory Limit: 512M
Memory Reservation: 256M
CPU Limit: 0.5
CPU Reservation: 0.25
```

**Deployment Settings:**
```yaml
Restart Policy: unless-stopped
Max Restart Attempts: 5
```

### 6. Volume Mounts

**Persistent Storage:**
```yaml
- Source: /app/logs
  Target: /app/logs
  Type: Volume
  Name: mevzuat-logs
```

### 7. Network Configuration

**Network Mode:**
- Use default Coolify network
- Auto-assign container name
- Enable Traefik routing

### 8. Deployment Webhooks

**Auto-Deployment:**
```bash
Webhook URL: https://coolify.software.vision/webhooks/deploy/{app-uuid}
Branch: main
Auto Deploy on Push: ✅
```

### 9. Validation & Testing

**Pre-Deployment Checklist:**
- [ ] Repository access verified
- [ ] All environment variables set
- [ ] Domain DNS configured
- [ ] Health check path accessible
- [ ] Port 8000 exposed correctly

**Post-Deployment Tests:**
```bash
# Health check
curl https://mcp-mevzuat.dosya.ai/health

# API endpoint test
curl -X POST https://mcp-mevzuat.dosya.ai/api/search \
  -H "Content-Type: application/json" \
  -H "Origin: https://flowise.software.vision" \
  -d '{"phrase": "test", "page_size": 1}'

# CORS verification
curl -H "Origin: https://flowise.software.vision" \
  https://mcp-mevzuat.dosya.ai/api/types
```

### 10. Expected Results

**Successful Deployment Indicators:**
- ✅ Container Status: `running:healthy`
- ✅ SSL Certificate: Auto-generated
- ✅ Health Check: Passing every 30s
- ✅ CORS Headers: Allowing flowise.software.vision
- ✅ API Responses: JSON format with proper data

**Application URLs:**
- **Main API**: `https://mcp-mevzuat.dosya.ai`
- **Health Check**: `https://mcp-mevzuat.dosya.ai/health`  
- **API Search**: `https://mcp-mevzuat.dosya.ai/api/search`
- **API Types**: `https://mcp-mevzuat.dosya.ai/api/types`

### 11. Flowise Integration

**HTTP Request Node Configuration:**
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

### 12. Monitoring & Logs

**Log Access:**
- Container logs: Coolify dashboard
- Application logs: `/app/logs/web_server.log`
- Health status: Real-time in dashboard

**Alerts Setup:**
- Health check failures
- High memory usage (>80%)
- Deployment failures
- SSL certificate expiry

---

## 🔧 Troubleshooting

**Common Issues:**

1. **Build Failure:**
   - Check Dockerfile syntax
   - Verify requirements.txt packages
   - Check Python version compatibility

2. **Health Check Failing:**
   - Verify `/health` endpoint responds
   - Check if application starts on port 8000
   - Review container logs

3. **CORS Errors:**
   - Verify ALLOWED_ORIGINS environment variable
   - Check Origin header in requests
   - Confirm domain spelling

4. **SSL Issues:**
   - Wait 2-3 minutes for certificate generation
   - Verify DNS is pointing correctly
   - Check Cloudflare tunnel status

Bu adımları takip ederek `mcp-mevzuat.dosya.ai` domain'inde başarılı bir deployment elde edebilirsiniz.
