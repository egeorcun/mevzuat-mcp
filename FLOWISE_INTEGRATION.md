# Flowise Entegrasyon Rehberi

Bu rehber, Mevzuat API Server'ı Flowise ile nasıl entegre edeceğinizi açıklar.

## 🔗 Flowise'a Bağlanma

### 1. HTTP Request Node Kullanma

Flowise'da **HTTP Request** node'unu kullanarak API'mıza bağlanabilirsiniz.

#### Temel Ayarlar

```json
{
  "method": "POST",
  "url": "https://your-mevzuat-api-domain.com/api/search",
  "headers": {
    "Content-Type": "application/json",
    "Accept": "application/json"
  }
}
```

### 2. Arama Endpoint'i

#### Search Request

```javascript
// Flowise'da HTTP Request node'unda kullanacağınız body
{
  "phrase": "{{$input}}",  // Kullanıcıdan gelen arama terimi
  "page_size": 5,
  "sort_field": "RESMI_GAZETE_TARIHI",
  "sort_direction": "desc"
}
```

#### Response Format

```json
{
  "documents": [
    {
      "mevzuat_id": "343829",
      "mevzuat_no": 5237,
      "mevzuat_adi": "Türk Ceza Kanunu",
      "mevzuat_tur": {
        "id": 1,
        "name": "KANUN",
        "description": "Kanun"
      },
      "resmi_gazete_tarihi": "2004-10-12T00:00:00",
      "resmi_gazete_sayisi": "25611"
    }
  ],
  "total_results": 150,
  "current_page": 1,
  "page_size": 5,
  "total_pages": 30
}
```

### 3. İçerik Alma Endpoint'i

#### Full Document Content

```javascript
// GET request
{
  "method": "GET",
  "url": "https://your-mevzuat-api-domain.com/api/legislation/{{mevzuat_id}}/content"
}
```

#### Specific Article Content

```javascript
// GET request
{
  "method": "GET", 
  "url": "https://your-mevzuat-api-domain.com/api/legislation/{{mevzuat_id}}/article/{{madde_id}}"
}
```

## 🏗️ Flowise Workflow Örnekleri

### 1. Basit Mevzuat Arama

```
[User Input] → [HTTP Request: Search] → [Data Transformation] → [LLM Processing] → [Output]
```

**HTTP Request Node Ayarları:**
- URL: `https://your-api.com/api/search`
- Method: `POST`
- Body: `{"phrase": "{{$input}}", "page_size": 3}`

**Data Transformation (Function Node):**
```javascript
// Search sonuçlarını LLM için hazırla
const results = $input.documents.map(doc => ({
  title: doc.mevzuat_adi,
  id: doc.mevzuat_id,
  date: doc.resmi_gazete_tarihi,
  type: doc.mevzuat_tur.description
}));

return {
  search_results: results,
  total_found: $input.total_results,
  formatted_text: results.map(r => 
    `${r.title} (${r.type}) - ${r.date}`
  ).join('\n')
};
```

### 2. Detaylı İçerik Analizi

```
[User Query] → [Search] → [Get Content] → [LLM Analysis] → [Response]
```

**Workflow Steps:**

1. **İlk HTTP Request (Arama):**
   ```json
   {
     "url": "/api/search",
     "method": "POST",
     "body": {"phrase": "{{user_query}}", "page_size": 1}
   }
   ```

2. **İkinci HTTP Request (İçerik):**
   ```json
   {
     "url": "/api/legislation/{{first_result_id}}/content",
     "method": "GET"
   }
   ```

3. **LLM Prompt:**
   ```
   Aşağıdaki mevzuat metnini analiz et ve kullanıcının "{{user_query}}" sorusunu yanıtla:
   
   {{content.markdown_content}}
   
   Kullanıcı Sorusu: {{user_query}}
   ```

### 3. Çoklu Mevzuat Karşılaştırma

```
[User Input] → [Search Multiple] → [Get Contents] → [Compare] → [Summary]
```

**Function Node (Çoklu Arama):**
```javascript
async function searchMultiple(query) {
  const searches = [
    { phrase: query, mevzuat_turleri: ["KANUN"] },
    { phrase: query, mevzuat_turleri: ["YONETMELIK"] }
  ];
  
  const results = [];
  for (const search of searches) {
    const response = await fetch('/api/search', {
      method: 'POST',
      body: JSON.stringify(search)
    });
    results.push(await response.json());
  }
  
  return results;
}
```

## 🔧 Gelişmiş Kullanım

### 1. Conditional Logic Node ile Akıllı Yönlendirme

```javascript
// Conditional Logic Node
if ($input.total_results === 0) {
  return "no_results";
} else if ($input.total_results === 1) {
  return "single_result";
} else {
  return "multiple_results";
}
```

### 2. Memory ve Context Yönetimi

**Conversation Memory:**
- Son aranan mevzuatları hatırla
- Kullanıcı context'ini koru
- İlgili mevzuatlar arasında bağlantı kur

**Vector Store Integration:**
```javascript
// Mevzuat içeriklerini vector store'a kaydet
{
  "text": content.markdown_content,
  "metadata": {
    "mevzuat_id": content.mevzuat_id,
    "title": document.mevzuat_adi,
    "type": document.mevzuat_tur.name,
    "date": document.resmi_gazete_tarihi
  }
}
```

### 3. Error Handling

**Function Node (Error Handler):**
```javascript
try {
  const response = await fetch(api_url, config);
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return await response.json();
} catch (error) {
  return {
    error: true,
    message: "Mevzuat API'sine erişimde sorun yaşandı. Lütfen daha sonra tekrar deneyin.",
    details: error.message
  };
}
```

## 📚 API Endpoint'leri Reference

### Search Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Mevzuat arama |
| `/api/types` | GET | Mevzuat türleri listesi |

### Content Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/legislation/{id}/content` | GET | Tam mevzuat içeriği |
| `/api/legislation/{id}/structure` | GET | Mevzuat yapısı (TOC) |
| `/api/legislation/{id}/article/{article_id}` | GET | Belirli madde içeriği |

### Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Sistem durumu |
| `/` | GET | API bilgileri |

## 🎯 Use Case Örnekleri

### 1. Hukuk Danışman Botu

```
"Boşanma davalarında mal rejimi nasıl belirlenir?"
→ Search: "boşanma mal rejimi"
→ Get relevant articles
→ LLM analysis with legal context
→ Structured legal advice
```

### 2. Mevzuat Güncellik Kontrolü

```
"5237 sayılı kanunun son hali nedir?"
→ Search by number: "5237"
→ Get full content
→ Check publication date
→ Summarize recent changes
```

### 3. Karşılaştırmalı Analiz

```
"İş kanunu ve sendikalar kanunu arasındaki farklar"
→ Search: "iş kanunu"
→ Search: "sendikalar kanunu"
→ Get both contents
→ LLM comparison analysis
→ Highlight differences
```

## 🔍 Debug ve Test

### Flowise Debug Modu

1. HTTP Request node'larında **Debug Mode**'u aktifleştirin
2. Response'ları **Console** node ile logla
3. **Variable Inspector** ile data flow'u takip edin

### Test Senaryoları

```javascript
// Test data for development
const testQueries = [
  "anayasa",
  "türk ceza kanunu",
  "iş kanunu 4857",
  "kadına yönelik şiddet"
];
```

Bu entegrasyon ile Flowise'da güçlü Türk mevzuatı analiz botları oluşturabilirsiniz!
