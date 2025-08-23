# Mevzuat API Server: Türk Mevzuatı için RESTful API

Bu proje, Adalet Bakanlığı'na ait Mevzuat Bilgi Sistemi'ne (`mevzuat.gov.tr`) erişimi kolaylaştıran hem **MCP sunucusu** hem de **RESTful Web API** sağlar.

## 🚀 Coolify Deployment

### Hızlı Kurulum

1. **Coolify Dashboard**'da yeni application oluşturun
2. **Repository**: `https://github.com/egeorcun/mevzuat-mcp.git`
3. **Build Method**: `Docker Compose`
4. **Domain**: `mcp-mevzuat.dosya.ai`

### Environment Variables

Coolify'da aşağıdaki environment variables'ları ayarlayın:

```bash
# Güvenlik
SECRET_KEY=DC2kao9HUkksvEfUs7WcsPn_XLuI2gR8ctfkqx9dUkY

# CORS - Flowise entegrasyonu
ALLOWED_ORIGINS=https://flowise.software.vision,https://mcp-mevzuat.dosya.ai
```

### Flowise Entegrasyonu

**HTTP Request Node** ayarları:

```json
{
  "method": "POST",
  "url": "https://mcp-mevzuat.dosya.ai/api/search",
  "headers": {
    "Content-Type": "application/json",
    "Origin": "https://flowise.software.vision"
  },
  "body": {
    "phrase": "{{$input}}",
    "page_size": 5
  }
}
```

## 🔧 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/health` | GET | Sistem durumu |
| `/api/search` | POST | Mevzuat arama |
| `/api/legislation/{id}/content` | GET | Tam mevzuat içeriği |
| `/api/legislation/{id}/structure` | GET | Mevzuat yapısı |
| `/api/types` | GET | Mevzuat türleri |

## 📋 MCP Client Desteği

MCP protokolü ile kullanmak için:

```bash
python mevzuat_mcp_server.py
```

## 🧪 Test

```bash
# Health check
curl https://mcp-mevzuat.dosya.ai/health

# API test
curl -X POST https://mcp-mevzuat.dosya.ai/api/search \
  -H "Content-Type: application/json" \
  -H "Origin: https://flowise.software.vision" \
  -d '{"phrase": "anayasa", "page_size": 2}'
```

📜 **Lisans**: MIT
