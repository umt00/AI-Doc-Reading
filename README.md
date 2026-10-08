# 📄 AI-Doc-Reading — Akıllı Doküman Okuma API (PoC / Prototip)

[![CI](https://github.com/umt00/AI-Doc-Reading/actions/workflows/ci.yml/badge.svg)](https://github.com/umt00/AI-Doc-Reading/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure AI](https://img.shields.io/badge/Azure-Document%20Intelligence-0078D4.svg?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-412991.svg?logo=openai&logoColor=white)](https://openai.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.9+-E92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Azure AI Document Intelligence** ve **Azure OpenAI (GPT-4o)** kullanarak fatura, irsaliye ve ticari belgelerden önceden model eğitimi gerektirmeksizin (**Train-Free / Zero-Shot**) yapılandırılmış veri ayıklayan yüksek performanslı REST API prototipi.

---

## 📌 Prototip / PoC Hakkında

Bu proje, geleneksel OCR ve özel model eğitimi (custom model training) yaklaşımlarının getirdiği yüksek maliyet, etiketleme eforu ve format bağımlılığı sorunlarını çözmek amacıyla geliştirilmiş bir **kavram kanıtı (Proof of Concept)** çalışmasıdır.

### 💡 Temel Tasarım İlkeleri

1. **Train-Free / Zero-Shot Yaklaşım:** Yüzlerce fatura örneğiyle özel model eğitmek veya şablon hazırlamak gerekmez. GPT-4o'nun anlamsal anlama kabiliyeti sayesinde değişen fatura formatlarına anında uyum sağlar.
2. **Akıllı Yönlendirici (Maliyet Optimizasyonu):** Azure Document Intelligence'ın **Layout** modeli ($10 / 1.000 sayfa) ile **Read** modeli ($1 / 1.000 sayfa) arasında içerik ve format sezgilerine (heuristics) göre dinamik yönlendirme yaparak işletme maliyetini **%90'a varan oranda** düşürür.
3. **Deterministik & Halüsinasyonsuz Çıktı:** Katı system prompt kuralları ve Pydantic v2 şeması ile LLM çıktısı sınırlandırılır; dokümanda yer almayan hiçbir veri türetilmez (`null` döner).
4. **Tip Güvenliği ve Doğrulama:** Sayısal tutarlar `Decimal`, tarihler ISO standart formatı (`YYYY-MM-DD`), Türk vergi formatları (VKN/TCKN) string olarak tip korumalı doğrulanır.

---

## 🏗️ Mimari ve İşlem Akışı

```
                           ┌──────────────────────────┐
                           │   İstemci (HTTP POST)    │
                           │   PDF, PNG, JPEG, TIFF   │
                           └────────────┬─────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   1. Doğrulama Katmanı       │
                         │   • Boyut & Boş dosya testi  │
                         │   • Magic bytes MIME tespiti │
                         │   • PDF şifre & başlık test  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   2. Akıllı Yönlendirici     │
                         │   • MIME/Boyut analizi       │
                         │   • Heuristic anahtar kelime │
                         └──────┬────────────────┬──────┘
                                │                │
              (Basit / Düz Metin)                (Tablolu / Karmaşık / Görsel)
                                ▼                ▼
                        ┌──────────────┐  ┌──────────────┐
                        │ Azure Read   │  │ Azure Layout │
                        │  ($1 / 1K)   │  │  ($10 / 1K)  │
                        └──────┬───────┘  └──────┬───────┘
                               │                 │
                               └────────┬────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │    Markdown Metin Çıktısı    │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   3. Azure OpenAI (GPT-4o)   │
                         │   • Zero-Shot JSON Extraction│
                         │   • Temperature = 0.0        │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   4. Pydantic v2 Doğrulama   │
                         │   • FaturaKalemi / Totals    │
                         │   • Standart APIResponse[T]  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     200 OK — JSON Yanıt      │
                         └──────────────────────────────┘
```

---

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.11+ veya Docker & Docker Compose
- Azure Document Intelligence servisi (Endpoint & API Key)
- Azure OpenAI servisi (GPT-4o dağıtımı, Endpoint & API Key)

---

### Yöntem 1: Docker Compose (Önerilen)

```bash
# 1. Repoyu klonlayın
git clone https://github.com/umt00/AI-Doc-Reading.git
cd AI-Doc-Reading

# 2. Ortam değişkenlerini yapılandırın
cp .env.example .env
# .env dosyasını favori editörünüzle açıp Azure kimlik bilgilerinizi girin

# 3. Docker konteynerini derleyip çalıştırın
docker compose up --build
```

API hazır: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Yöntem 2: Yerel Geliştirme (`uv` ile)

Modern ve hızlı paket yöneticisi [astral-sh/uv](https://github.com/astral-sh/uv) kullanılması önerilir:

```bash
# 1. uv kurulu değilse yükleyin
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Sanal ortamı oluşturun ve geliştirici paketlerini kurun
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Ortam değişkenlerini hazırlayın
cp .env.example .env
# .env dosyasını düzenleyin

# 4. API sunucusunu başlatın
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ⚙️ Ortam Değişkenleri (.env)

`.env` dosyasında yer alan ayarlar ve varsayılanları:

| Parametre | Zorunlu | Varsayılan | Açıklama |
|---|:---:|:---:|---|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | ✅ | - | Azure Document Intelligence endpoint URL |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | ✅ | - | Azure Document Intelligence API anahtarı |
| `AZURE_OPENAI_ENDPOINT` | ✅ | - | Azure OpenAI servis endpoint URL |
| `AZURE_OPENAI_API_KEY` | ✅ | - | Azure OpenAI API anahtarı |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | ❌ | `gpt-4o` | Model deployment adı |
| `AZURE_OPENAI_API_VERSION` | ❌ | `2024-08-01-preview` | Azure OpenAI REST API versiyonu |
| `MAX_FILE_SIZE_MB` | ❌ | `50` | İzin verilen maksimum dosya boyutu (MB) |
| `LOG_LEVEL` | ❌ | `INFO` | Log seviyesi (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ALLOWED_ORIGINS` | ❌ | `*` | CORS izinli origin listesi (virgülle ayrılmış) |
| `UVICORN_HOST` | ❌ | `0.0.0.0` | Sunucu bind adresi |
| `UVICORN_PORT` | ❌ | `8000` | Sunucu port numarası |

---

## 📡 API Kullanımı

### 1. Sağlık Kontrolü (`/health`)

Servisin ve Azure entegrasyonlarının çalışma durumunu döner. Azure bilgileri girilmemişse `degraded` modda çalışır.

```bash
curl http://localhost:8000/health
```

**Örnek Yanıt:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "ocr_service": "ready",
    "llm_service": "ready",
    "router_service": "ready"
  }
}
```

---

### 2. Doküman Veri Ayıklama (`/api/v1/extract`)

Fatura veya irsaliye dosyasını `multipart/form-data` olarak gönderir.

```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "accept: application/json" \
  -F "file=@ornek_fatura.pdf"
```

**Örnek Başarılı Yanıt (200 OK):**
```json
{
  "success": true,
  "data": {
    "dokuman_tipi": "e-Fatura",
    "fatura_no": "GIB2024000001234",
    "tarih": "2024-03-15",
    "vade_tarihi": "2024-04-15",
    "tedarikci_unvan": "Örnek Bilişim Teknolojileri A.Ş.",
    "tedarikci_vkn": "1234567890",
    "tedarikci_adres": "Maslak Mah. Büyükdere Cad. No:1 Sarıyer / İstanbul",
    "alici_unvan": "Alıcı Ticaret Ltd. Şti.",
    "alici_vkn": "9876543210",
    "alici_adres": "Çankaya / Ankara",
    "kalemler": [
      {
        "urun_adi": "Bulut Sunucu Hizmeti - 1 Yıllık",
        "adet": 1.0,
        "birim": "Adet",
        "birim_fiyat": 24000.0,
        "kdv_orani": 20.0,
        "toplam_tutar": 28800.0
      }
    ],
    "ara_toplam": 24000.0,
    "kdv_toplam": 4800.0,
    "genel_toplam": 28800.0,
    "para_birimi": "TRY",
    "notlar": "Ödeme banka havalesi ile yapılmıştır."
  },
  "metadata": {
    "dosya_adi": "ornek_fatura.pdf",
    "dosya_boyutu_kb": 182.4,
    "sayfa_sayisi": 1,
    "kullanilan_model": "prebuilt-layout",
    "llm_model": "gpt-4o",
    "islem_suresi_sn": 5.42,
    "llm_token_kullanimi": {
      "prompt_tokens": 1280,
      "completion_tokens": 310,
      "total_tokens": 1590
    },
    "islem_zamani": "2026-10-08T10:15:30.123456Z"
  }
}
```

---

## 🧪 Test ve Kod Kalitesi

Projede birim ve entegrasyon testleri için `pytest`, statik kod analizi ve biçimlendirme için `ruff` yapılandırılmıştır.

```bash
# Testleri çalıştır (25 test)
uv run pytest

# Ruff ile linter denetimi
uv run ruff check .

# Otomatik biçimlendirme ve düzeltme
uv run ruff check --fix .
```

---

## 📂 Dizin Yapısı

```
AI-Doc-Reading/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline
├── src/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings ortam yönetimi
│   ├── main.py                 # FastAPI uygulaması & pipeline orkestrasyonu
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── extraction.py       # Fatura & İrsaliye Pydantic modelleri
│   │   └── response.py         # Standart API yanıt şemaları
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py      # Azure Document Intelligence (Layout/Read)
│   │   ├── router_service.py   # Sezgisel (heuristic) akıllı yönlendirici
│   │   └── llm_service.py      # Azure OpenAI deterministik LLM extraction
│   └── utils/
│       ├── __init__.py
│       └── validators.py       # Magic bytes, boyut, PDF şifre & başlık kontrolü
├── tests/
│   ├── test_api.py             # FastAPI endpoint testleri
│   ├── test_router.py          # Yönlendirici heuristic testleri
│   ├── test_schemas.py         # Veri şeması & tip dönüşüm testleri
│   └── test_validators.py      # Dosya doğrulama testleri
├── .dockerignore
├── .env.example                # Örnek ortam değişkenleri şablonu
├── .gitignore
├── Dockerfile                  # Multi-stage güvenli üretim Dockerfile
├── docker-compose.yml          # Konteyner orkestrasyonu
├── pyproject.toml              # Paket & bağımlılık yönetimi
├── requirements.txt            # Dondurulmuş temel bağımlılıklar
├── LICENSE                     # MIT Açık Kaynak Lisansı
└── README.md
```

---

## 🗺️ Prototip Sınırları & Üretim Yol Haritası (Roadmap)

Bu proje bir prototip olarak tasarlanmıştır. Canlı kurumsal ortama (Production) alınırken planlanan geliştirmeler:

- [ ] **Asenkron Görev Kuyruğu (Task Queue):** Çok sayfalı (50+ sayfa) dokümanlar için Celery + Redis veya Azure Service Bus entegrasyonu ile arka plan işleme (`job_id` ile asenkron sorgulama).
- [ ] **Webhook Bildirimleri:** İşlem tamamlandığında kurumsal ERP/CRM sistemlerine bildirim gönderimi.
- [ ] **Çoklu Doküman Tipi Genişletmesi:** Makbuz, sözleşme, gümrük beyannamesi ve banka dekontları için genişletilmiş Pydantic şablonları.
- [ ] **Akıllı Sayfa Bölme (Page Splitting):** Tek bir PDF içerisindeki birden fazla faturayı ayırt edip ayrı ayrı işleme.
- [ ] **Audit Trail & Metrikler:** Prometheus / OpenTelemetry entegrasyonu ile sayfa başına maliyet ve yanıt sürelerinin izlenmesi.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak sunulmaktadır.
