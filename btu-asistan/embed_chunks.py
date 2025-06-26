# embed_chunks.py

import os, json, pathlib
from typing import List

import chromadb
from chromadb.errors import NotFoundError
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI

#.env ve ayarlar 
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMB_MODEL      = os.getenv("EMB_MODEL",  "text-embedding-3-large")
BATCH_SIZE     = int(os.getenv("EMB_BATCH", 100))

if not OPENAI_API_KEY:
    raise SystemExit(" OPENAI_API_KEY tanımlı değil (.env).")

CLIENT_OA = OpenAI(api_key=OPENAI_API_KEY) 

# ChromaDB ayarları
COLL_NAME   = "btu_yonetmelik"
PERSIST_DIR = "chroma_store"


chroma = chromadb.PersistentClient(path=PERSIST_DIR)

try: chroma.delete_collection(COLL_NAME)
except NotFoundError: pass

try: 
    collection = chroma.get_collection(COLL_NAME)
except NotFoundError:
    collection = chroma.create_collection(COLL_NAME)

# Parçaları okuma bölümü
chunks_path = pathlib.Path("chunks.json")
chunks: List[dict] = json.loads(chunks_path.read_text("utf-8"))

print(f"{len(chunks)} chunk okunuyor → embedding başlıyor…")


def batched(lst, n): 
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

embed_id_counter = 0  

for batch in tqdm(list(batched(chunks, BATCH_SIZE)), desc="Embedding"): 
    texts = [c["Metin"] for c in batch]
    
    
    resp  = CLIENT_OA.embeddings.create( 
        model = EMB_MODEL,
        input = texts
    )
    vectors = [d.embedding for d in resp.data]

    ids, metas = [], []
    for c in batch:
        ids.append(f"chunk-{embed_id_counter}")
        embed_id_counter += 1
        # Meta verileri hazırlama
        metas.append({ 
            "file":      c["Dosya Adı"],
            "page":      c["Sayfa No"],
            "madde_no":  c["Madde No"],
        })
        
    # Vektörleri ChromaDB koleksiyonuna ekleme
    collection.add(
        ids        = ids,
        embeddings = vectors,
        documents  = texts,
        metadatas  = metas,
    )

print(f" Yükleme tamam: koleksiyonda {collection.count()} vektör var.")
