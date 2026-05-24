import sys
from pathlib import Path

pdf_path = Path(r"C:\Users\gustavo.telles\Desktop\CryptoETL\CryptoETL_Apresentacao.pdf")
out_path = Path(r"C:\Users\gustavo.telles\Desktop\CryptoETL\reports\screenshots\presentation_text.txt")
out_path.parent.mkdir(parents=True, exist_ok=True)

try:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        from pypdf import PdfReader
except Exception:
    print('NO_PDF_LIB')
    sys.exit(2)

try:
    reader = PdfReader(str(pdf_path))
    texts = []
    for i, page in enumerate(reader.pages):
        texts.append(f'--- PAGE {i+1} ---')
        try:
            t = page.extract_text()
        except Exception:
            t = None
        texts.append(t or '')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(texts))
    print('OK', out_path)
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
