# bot.py  —  BTÜ Lisans Yönetmelik Telegram Botu 
import os, re, asyncio, chromadb
from dotenv import load_dotenv
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)
from telegram.constants import ChatAction  

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.documents import Document

#.env ayarları
load_dotenv()
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
OA_KEY   = os.getenv("OPENAI_API_KEY")
if not TG_TOKEN or not OA_KEY:
    raise SystemExit("TELEGRAM_TOKEN veya OPENAI_API_KEY tanımlı değil!")

LLM = ChatOpenAI(model_name="gpt-4.1", temperature=0)
EMB = OpenAIEmbeddings(model="text-embedding-3-large")
# ChromaDB istemcisi ve vektör veritabanı
client = chromadb.PersistentClient(path="chroma_store") 
vectordb = Chroma(
    client            = client,
    collection_name   = "btu_yonetmelik",
    embedding_function= EMB
)

THRESH = 0.1   # Benzerlik eşiği


MAX_HISTORY = 10   # Sohbet geçmişi sınırı

# Sohbet geçmişini getirir oluşturur
def get_message_history(chat_data: Dict[str, Any]) -> List:   
    """Sohbet geçmişini al veya başlat"""
    if 'history' not in chat_data:
        chat_data['history'] = []
    return chat_data['history']

def update_history(chat_data: Dict[str, Any], user_msg: str, bot_msg: str):
    """Geçmişi güncelle (yeni mesajları ekle ve boyutu sınırla)"""
    history = chat_data['history']
    
    # Yeni mesajları ekle
    history.append(HumanMessage(content=user_msg)) # 
    history.append(AIMessage(content=bot_msg)) # 
    
    # Geçmişi sınırla
    if len(history) > MAX_HISTORY:
        chat_data['history'] = history[-MAX_HISTORY:]

# Sohbet zincirleri oluşturma fonksiyonları
def create_regulation_chain():
    """Yönetmelik sorguları için zincir oluşturma """
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            "Sen BTÜ lisans yönetmelik asistanısın. "
            "Lutfen soruyu önce anlamlandır sonra dosyalardan en alakalı kısmı baz alarak yanıtla."
            "- Teşekkür, memnuniyet ifadeleri ve genel sohbet mesajlarında 'İlgili madde:' bilgisini sakın kullanma ve ekleme"
            "Eğer tam olarak dosyalardan ilgili veriyi bulamıyorsan 'Üzgünüm yönetmelik dosyalarında bu konuya dair bir bilgi bulamadım.' şeklinde cevap ver. Ve asla 'İlgili madde:' bilgisini ekleme."
            "Eğer kullanıcı bir önceki cevapa atıfta bulunursa, lütfen bu atıfı dikkate alarak önceki soruyu ve cevabı dikkate alarak ve tekrar dosya taraması yaparak yanıt ver."
            "Kullanıcı cevaptan emin değilse, lüfen daha detaylı bilgi ver veya ilgili maddeyi belirt."
            "Aşağıdaki bağlamı ve sohbet geçmişini kullanarak soruyu yanıtla."
            "Her iddiadan sonra ilgili maddeyi, fıkrayı ve varsa benti belirt ama referans numarası kullanma."
            "Her yanıtın sonunda 'İlgili madde:' başlığı ile dosya adı, sayfa numarası, madde, fıkra ve bent bilgilerini belirt."
            "Bilgi kaynağı veya kaynak listesi ekleme."
            ),
        MessagesPlaceholder(variable_name="history"),
        ("system", "Bağlam:\n{context}"),
        ("human", "Soru: {question}")
    ])
    
    return (
        RunnablePassthrough.assign( context=lambda x: format_context(x["docs"]))| prompt | LLM | StrOutputParser()
    )

def create_chat_chain():
    """Yönetmelik dışı sohbet mesajları için zincir oluşturma"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            "Sen yardımsever, samimi bir sohbet asistanısın.\n"
            "- BTÜ Yönetmelik Botu olduğunu unutma\n"
            "- Selamlaşmalara dostça karşılık ver ve 'Merhaba! Ben BTU Yönetmelik Asistanınız. Aklınıza takılan soruları sormaktan çekinmeyin!' gibi bir yanıt ver."
            "- Teşekkür, memnuniyet ifadeleri ve genel sohbet mesajlarında 'İlgili madde:' bilgisini sakın kullanma ve ekleme"
            "- Eğer kullanıcı bir önceki cevapa atıfta bulunursa, lütfen bu atıfı dikkate alarak önceki soruyu ve cevabı dikkate alarak ve tekrar dosya taraması yaparak yanıt ver.\n"
            "- Kullanıcı cevaptan emin değilse, lüfen daha detaylı bilgi ver veya ilgili maddeyi belirt.\n"
            "- Yönetmelik dışı sorularda kibarca yönlendir yap"
            "'ilgili madde:' bilgisini sakın kullanma ve ekleme"
            ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ])
    
    return prompt | LLM | StrOutputParser()

def format_context(docs: List[Document]) -> str:
    """Belgeleri formatlı metne dönüştürme işlemi"""
    context_parts = []
    for doc in docs:
        # Metadata'dan dosya adını al
        file_name = doc.metadata.get('file', 'Bilinmeyen Dosya')
        page_no = doc.metadata.get('page', '')
        madde_no = doc.metadata.get('madde_no', '')
        
        # Bağlam metni oluştur
        context_part = f"[Dosya: {file_name}"
        if page_no:
            context_part += f", Sayfa: {page_no}"
        if madde_no:
            context_part += f", Madde: {madde_no}"
        context_part += f"]\n{doc.page_content}"
        
        context_parts.append(context_part)
    
    return "\n\n".join(context_parts)

# Telegram Bot Fonksiyonları
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Ben BTÜ Yönetmelik Asistanınız.🤖\n"
        "Yönetmelikle ilgili sorularınızı açık ve net bir şekilde yazarsanız yardımcı olabilirim."
    )

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    chat_id = update.message.chat_id
    
    # Yazıyor...
    await ctx.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    # Belleği yönet
    history = get_message_history(ctx.chat_data)
    
    # Yönetmelik belge arama
    pairs = vectordb.similarity_search_with_relevance_scores(user_msg, k=6)
    docs = [doc for doc, score in pairs if score >= THRESH]

    if docs:
        # Yönetmelik zinciri
        regulation_chain = create_regulation_chain()
        context = {
            "question": user_msg,
            "docs": docs,
            "history": history
        }
        
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None, lambda: regulation_chain.invoke(context))

        
        await update.message.reply_text(answer)
        update_history(ctx.chat_data, user_msg, answer)
        return

    # Sohbet mesajları (yönetmelik dışı)
    chat_chain = create_chat_chain()
    context = {
        "question": user_msg,
        "history": history
    }
    
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(
        None, lambda: chat_chain.invoke(context))
    
    
    await update.message.reply_text(answer)
    update_history(ctx.chat_data, user_msg, answer)


def main():
    app = ApplicationBuilder().token(TG_TOKEN).build() 
    app.add_handler(CommandHandler("start", start)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))  
    print("🤖 Bot çalışıyor...")
    app.run_polling() 

if __name__ == "__main__":
    main()