# 🔍 Penta Document Intelligence

> Azure AI Document Intelligence + Azure OpenAI ile **train-free / zero-shot** akıllı doküman işleme REST API

## 📋 Genel Bakış

Bu servis, fatura ve irsaliye dokümanlarından otomatik veri ayıklama yapar:

- **Azure Document Intelligence** — Layout/Read modeli ile OCR analizi
- **Azure OpenAI (GPT-4o)** — Zero-shot LLM extraction
- **Pydantic v2** — Tip güvenli veri doğrulama
- **FastAPI** — Yüksek performanslı REST API

### İşlem Akışı

```
Dosya Yükleme → Doğrulama → Akıllı Yönlendirme → OCR → LLM Extraction → JSON Çıktı
```

## 🚀 Kurulum ve Çalıştırma

### Yöntem 1: Docker (Önerilen)

```bash
# 1. Repoyu klonla
git clone <repo-url>
cd penta-document-intelligence

# 2. Ortam değişkenlerini yapılandır
cp .env.example .env
# .env dosyasını düzenle — Azure endpoint ve key'leri gir

# 3. Docker ile başlat
docker compose up --build

# API hazır: http://localhost:8000/docs
```

### Yöntem 2: Yerel Geliştirme (uv)

```bash
# 1. uv kurulumu (yoksa)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Sanal ortam ve bağımlılıklar
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 3. Ortam değişkenleri
cp .env.example .env
# .env dosyasını düzenle

# 4. Sunucuyu başlat
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# API hazır: http://localhost:8000/docs
```

## ⚙️ Konfigürasyon

`.env` dosyasında aşağıdaki değişkenler tanımlanmalıdır:

| Değişken | Zorunlu | Açıklama |
|----------|---------|----------|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | ✅ | Document Intelligence endpoint URL |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | ✅ | Document Intelligence API key |
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | ❌ | Model adı (varsayılan: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | ❌ | API versiyonu (varsayılan: `2024-08-01-preview`) |
| `MAX_FILE_SIZE_MB` | ❌ | Max dosya boyutu (varsayılan: `50`) |
| `LOG_LEVEL` | ❌ | Log seviyesi (varsayılan: `INFO`) |

## 📡 API Kullanımı

### Health Check

```bash
curl http://localhost:8000/health
```

### Doküman Veri Ayıklama

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@fatura.pdf" \
  -H "accept: application/json"
```

### Örnek Yanıt

```json
{
  "success": true,
  "data": {
    "dokuman_tipi": "e-Fatura",
    "fatura_no": "FT2024000123",
    "tarih": "2024-01-15",
    "vade_tarihi": "2024-02-15",
    "tedarikci_unvan": "ABC Teknoloji A.Ş.",
    "tedarikci_vkn": "1234567890",
    "alici_unvan": "Penta Teknoloji A.Ş.",
    "alici_vkn": "0987654321",
    "kalemler": [
      {
        "urun_adi": "Sunucu Bakım Hizmeti",
        "adet": 1,
        "birim": "Adet",
        "birim_fiyat": 5000.00,
        "kdv_orani": 20,
        "toplam_tutar": 6000.00
      }
    ],
    "ara_toplam": 5000.00,
    "kdv_toplam": 1000.00,
    "genel_toplam": 6000.00,
    "para_birimi": "TRY"
  },
  "metadata": {
    "dosya_adi": "fatura.pdf",
    "dosya_boyutu_kb": 245.3,
    "sayfa_sayisi": 1,
    "kullanilan_model": "prebuilt-layout",
    "llm_model": "gpt-4o",
    "islem_suresi_sn": 8.45
  }
}
```

## 🏗️ Proje Yapısı

```
├── pyproject.toml              # uv bağımlılıkları
├── requirements.txt            # Dondurulmuş paketler
├── .env.example                # Konfigürasyon şablonu
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Docker Compose tanımı
└── src/
    ├── main.py                 # FastAPI app + pipeline
    ├── config.py               # pydantic-settings konfigürasyonu
    ├── schemas/
    │   ├── extraction.py       # Fatura/İrsaliye Pydantic modelleri
    │   └── response.py         # API yanıt formatları
    ├── services/
    │   ├── ocr_service.py      # Azure Document Intelligence
    │   ├── router_service.py   # Heuristic yönlendirici
    │   └── llm_service.py      # Azure OpenAI orchestration
    └── utils/
        └── validators.py       # Dosya doğrulama kontrolleri
```

## 🔄 Azure'a Taşıma

Projeyi Azure'a taşımak için:

1. **Azure Container Registry** oluşturun
2. Docker imajını build & push edin:
   ```bash
   docker build -t <acr-name>.azurecr.io/penta-doc-intelligence:latest .
   docker push <acr-name>.azurecr.io/penta-doc-intelligence:latest
   ```
3. **Azure Container Apps** veya **Azure Functions** (Container) üzerinde dağıtın
4. `.env` değişkenlerini Azure ortam değişkenleri olarak tanımlayın

> 💡 Kod değişikliği gerekmez — yalnızca `.env` dosyasındaki endpoint URL'leri güncellenir.

## 🧪 Test

```bash
# Swagger UI ile test
open http://localhost:8000/docs

# cURL ile PDF testi
curl -X POST http://localhost:8000/api/v1/extract \
  -F "file=@test_fatura.pdf"

# Health check
curl http://localhost:8000/health
```

## 📄 Lisans

Penta Teknoloji — Tüm hakları saklıdır.
