# Mevzuat MCP Server - Deployment Guide

Bu rehber, Mevzuat MCP Server'ın Coolify'da nasıl deploy edileceği ve Flowise ile nasıl entegre edileceği konusunda adım adım talimatlar içerir.

## 🚀 Coolify'da Deployment

### 1. Gereksinimler

- Çalışan bir Coolify instance'ı
- Git repository erişimi
- Docker desteği olan server

### 2. Coolify'da Uygulama Oluşturma

1. **Coolify Dashboard**'a giriş yapın
2. **New Application** butonuna tıklayın
3. **Source** olarak Git repository'yi seçin
4. Repository URL'ini girin: `https://github.com/your-username/mevzuat-mcp.git`
5. **Branch** olarak `main` seçin

### 3. Environment Variables Ayarlama

Coolify'da aşağıdaki environment variables'ları ayarlayın:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=2

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=production

# API Configuration
API_TIMEOUT=30.0

# CORS - Flowise domain'inizle değiştirin
ALLOWED_ORIGINS=https://your-flowise-domain.com,https://localhost:3000

# Security
SECRET_KEY=your-super-secret-key-here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=120
```

### 4. Build ve Deploy Ayarları

- **Build Command**: Docker Dockerfile kullanılacak
- **Start Command**: `./start.sh` (otomatik olarak algılanacak)
- **Port**: `8000`
- **Health Check**: `/health` endpoint'i

### 5. Domain Ayarlama

1. Coolify'da **Domains** sekmesine gidin
2. Subdomain ekleyin: `mevzuat-api.yourdomain.com`
3. SSL sertifikası otomatik olarak oluşturulacak

## 🔧 Yerel Development

### Docker ile Test

```bash
# Repository'yi klonlayın
git clone <repository-url>
cd mevzuat-mcp

# Docker image'ını build edin
docker build -t mevzuat-api .

# Container'ı çalıştırın
docker run -p 8000:8000 -e ENVIRONMENT=development mevzuat-api
```

### Docker Compose ile

```bash
# Docker compose ile çalıştırın
docker-compose up -d

# Logları kontrol edin
docker-compose logs -f mevzuat-api

# Durdurmak için
docker-compose down
```

### Manuel Setup

```bash
# Python sanal ortamı oluşturun
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows

# Bağımlılıkları kurun
pip install -r requirements.txt

# Environment variables'ları ayarlayın
cp env.example .env
# .env dosyasını düzenleyin

# Sunucuyu başlatın
python web_server.py
```

## 🔍 Health Check ve Monitoring

### Health Check Endpoint

```bash
curl https://your-domain.com/health
```

Response:
```json
{
  "status": "healthy",
  "message": "Mevzuat API Server is running",
  "timestamp": "2024-01-20T10:30:00"
}
```

### API Documentation

Production'da API docs devre dışıdır. Development için:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐛 Troubleshooting

### Yaygın Sorunlar

1. **Container başlamıyor**
   ```bash
   # Logları kontrol edin
   docker logs container-name
   ```

2. **Port erişim sorunu**
   - Firewall ayarlarını kontrol edin
   - Port binding'i doğrulayın

3. **SSL sertifika sorunları**
   - Domain DNS ayarlarını kontrol edin
   - Coolify SSL ayarlarını yenileyin

### Log Dosyaları

- Container logs: `docker logs container-name`
- Application logs: `/app/logs/web_server.log`
- Health check: `/health` endpoint'ini kullanın

## 📊 Performance Tuning

### Production Ayarları

```bash
# Gunicorn workers sayısını artırın
WORKERS=4

# Rate limiting ayarlayın
RATE_LIMIT_PER_MINUTE=200

# Timeout değerlerini optimize edin
API_TIMEOUT=45.0
```

### Resource Limits

Docker container için önerilen limits:
- Memory: 512MB-1GB
- CPU: 0.5-1 core
- Disk: 2GB minimum

## 🔒 Security

### Production Security Checklist

- [ ] `SECRET_KEY` güvenli bir değere ayarlandı
- [ ] `ALLOWED_ORIGINS` sadece gerekli domain'leri içeriyor
- [ ] `ENVIRONMENT=production` ayarlandı
- [ ] API docs disabled (otomatik)
- [ ] HTTPS enabled
- [ ] Rate limiting aktif
- [ ] Monitoring kuruldu

### Environment Variables Güvenliği

- Hiçbir zaman `.env` dosyasını git'e commit etmeyin
- Secret değerleri Coolify secrets manager'da saklayın
- Production ve development environment'ları ayırın
