# 📚 BTÜ Yapay Zeka Destekli Yönetmelik Botu

**Yapay zekâ destekli Telegram danışmanı – Bursa Teknik Üniversitesi’nde yönetmelik sorularına saniyeler içinde, madde referanslı olarak yanıtlar.**
<img src="https://github.com/aslanburak/BTU-Yonetmelik-TelegramBot/blob/main/btu-asistan/images/telegram1.jpg" width="600px" height="auto">
---

## Genel Bakış
Bu proje, BTÜ lisans/lisansüstü yönetmeliklerini semantik vektör uzayına aktararak Telegram üzerinden **anlık ve kaynak gösteren** danışmanlık sağlar.  
Kullanıcı sorusu → vektörleştirme → ChromaDB’de en yakın yönetmelik parçaları → GPT-4 tabanlı yanıt (+ dosya, sayfa, madde).

---

## Öne Çıkan Özellikler
- **Retrieval-Augmented Generation (RAG)** – doğru maddeyi bulur, GPT-4’e bağlam olarak geçirir  
- **Kaynak Şeffaflığı** – yanıt sonunda *dosya | sayfa | madde | fıkra* bilgisi  
- **LangChain Zincirleri** – Regulation Chain (RAG) + Chat Chain (genel mesaj)  
- **Düşük Maliyet** – demo testinde 0,05 $ ≈ 20 soru için 
- **Kolay Güncelleme** – yönetmelik değişince yalnızca embed hattı yeniden çalıştırılır  

---

## Dosya Yapısı
```
btu-asistan
│
├─ bot.py # Telegram botu & zincir çağrısı
├─ extract_pdf.py # PDF → ham metin için 
├─ segment_and_chunk_nofile.py  # segmentleme ve parçalama için
├─ embed_chunks.py # Embedding + Chroma yükleme 
├─ chroma_store/ # Kalıcı vektör koleksiyonu 
└─ pdfs/ # Kaynak yönetmelik PDF’leri
```


---

## Hızlı Kurulum
```bash
git clone https://github.com/aslanburak/BTU-Yonetmelik-TelegramBot.git
cd btu-asistan
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# API anahtarlarını ayarla (.env dosyası güvenlik açısından yüklenmedi)
.env dosyanızı oluşturun:
TELEGRAM_TOKEN=123456:ABC...
OPENAI_API_KEY=sk-...

# 1 | PDF'leri metne dönüştür
python extract_pdf.py pdfs/

# 2 | Segment + chunk + JSON
python segment_and_chunk_nofile.py

# 3 | Embedding & Chroma yükle
python embed_chunks.py

Bu adımlar tek seferliktir yönetmelik güncellenince yeniden çalıştırın.

python bot.py
# Konsolda: 🤖 Bot çalışıyor...