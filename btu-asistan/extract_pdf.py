# extract_pdf.py
from __future__ import annotations
import re, sys, pathlib, itertools
from typing import List
import pdfplumber
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None  

# ─── PDF’den metin çıkarma ve marker ekleme 
def pdf_to_text_with_marker(path: pathlib.Path) -> List[str]:
    out: List[str] = []
    with pdfplumber.open(path) as pdf: 
        for i, page in enumerate(pdf.pages, start=1):
            marker = f"[[FN:{path.name}|P:{i}]]" 

            txt = page.extract_text() or "" 
           
            if not txt.strip() and pytesseract:
                pil_img: Image.Image = page.to_image(resolution=300).original
                txt = pytesseract.image_to_string(pil_img, lang="tur")
                
            out.append(f"{marker}\n{txt}")
    return out

def clean_text(text: str) -> str:
    """Satır sonu tire birleşimleri, fazla boşluklar vb. düzelt."""
    text = re.sub(r"(\w)(?:\u00AD|-|–|—)\s*\n\s*(\w)", r"\1\2", text) 
    text = re.sub(r"[ \t]+\n", "\n", text)                             
    text = re.sub(r"\n{3,}", "\n\n", text)                             
    return text.strip()

#PDF Birleştirme ve temizleme
def merge_pdfs(pdf_dir: str = "pdfs") -> str: 
    dir_path = pathlib.Path(pdf_dir)
    
    pdf_paths = sorted(dir_path.glob("*.pdf"))
    
    print(f"🔎 {len(pdf_paths)} PDF bulundu, işleniyor…")
    pages: List[str] = list(itertools.chain.from_iterable(
        pdf_to_text_with_marker(p) for p in pdf_paths
    ))

    return clean_text("\n\n".join(pages))

if __name__ == "__main__":
    folder = "pdfs"
    combined = merge_pdfs(folder) 
    out_file = pathlib.Path("big_text.txt")
    out_file.write_text(combined, encoding="utf-8")
    print(f"✅ {out_file} dosyasına {len(combined):,} karakter yazıldı.")
