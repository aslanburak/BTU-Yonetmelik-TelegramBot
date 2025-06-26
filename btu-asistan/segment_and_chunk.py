# segment_and_chunk_nofile.py  
import json, re, bisect
from pathlib import Path
from typing import Dict, List
import tiktoken
from langchain.text_splitter import TokenTextSplitter

TXT_FILE = Path("big_text.txt") 
OUT_JSON = Path("chunks.json")

MAX_TOK   = 450
OVERLAP   = 50
ENC       = tiktoken.get_encoding("cl100k_base") 

RAW = TXT_FILE.read_text("utf-8") 

#Marker Pozisyonlarının Belirlenmesi
mark_rx = re.compile(r"\[\[FN:(?P<file>[^\|]+)\|P:(?P<page>\d+)\]\]\n?") 
pos, markers = [], [] 
for m in mark_rx.finditer(RAW): 
    pos.append(m.start()) 
    markers.append({"Dosya Adı": m["file"], "Sayfa No": int(m["page"])}) 


def meta_at(idx:int)->Dict:
    j = bisect.bisect_right(pos, idx)-1 
    return markers[max(j,0)].copy()


madde_rx = re.compile(r"(?m)^MADDE\s*[–—-]*\s*\d+", re.IGNORECASE)

starts: List[int] = []  

for madde_match in madde_rx.finditer(RAW): 
    madde_pos = madde_match.start()
    
    # MADDE'den önceki kısmı al
    before_madde = RAW[:madde_pos]
    
    
    lines = before_madde.rstrip().split('\n') 
    prev_line = ""
    prev_line_start = madde_pos
    
    # Geriye doğru git, boş olmayan ilk satırı bul
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():  
            prev_line = lines[i].strip()
            lines_before = lines[:i]
            if lines_before:
                prev_line_start = len('\n'.join(lines_before)) + 1
            else:
                prev_line_start = 0
            break
    
    if prev_line:
        # Başlıktan öncek satırın noktalama işaretiyle bitip bitmediğini kontrol et
        if prev_line.endswith(('.', ',', ':', ';', '!', '?')):
            starts.append(madde_pos)
        else:
          
            starts.append(prev_line_start)
    else:
        starts.append(0) 


ekler_rx = re.compile(r"(?m)^EKLER\s*:", re.IGNORECASE)
for m in ekler_rx.finditer(RAW):
    starts.append(m.start())


if not starts:
    starts = [0] 


starts = sorted(list(set(starts)))
starts.append(len(RAW))           

# ─── Token splitter 
tok_split = TokenTextSplitter(
    chunk_size    = MAX_TOK,
    chunk_overlap = OVERLAP,
    encoding_name = "cl100k_base",
)

mad_no_rx = re.compile(r"MADDE\s*[–—-]*\s*(\d+)", re.IGNORECASE)
 
# ─── Parçalama ve JSON çıktısı
chunks: List[Dict] = []   
for a, b in zip(starts, starts[1:]):  
    segment_raw = RAW[a:b] 

    mad_match = mad_no_rx.search(segment_raw)
    if mad_match:
        mad_no = int(mad_match.group(1))
    else:
        mad_no = 0  

    base_meta = meta_at(a) 
 
    clean_seg = mark_rx.sub("", segment_raw).strip()

    # Parçalara ayırma işlemi
    for piece in tok_split.split_text(clean_seg): 
        chunks.append({  
            "Dosya Adı": base_meta["Dosya Adı"],
            "Sayfa No":  base_meta["Sayfa No"],
            "Madde No":  mad_no, 
            "Metin":     piece.strip()
        })

# ─── JSON çıktısı
OUT_JSON.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), "utf-8")
print(f"✓ {len(chunks)} chunk '{OUT_JSON}' dosyasına kaydedildi.")