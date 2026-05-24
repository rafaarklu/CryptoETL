"""Extrai texto de RELATORIO_TECNICO.pdf e gera RELATORIO_TECNICO.md.

Uso: python scripts/extract_pdf_to_md.py
Se pypdf não estiver instalado, o script tentará instruir a instalação.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PDF_FILE = ROOT / "RELATORIO_TECNICO.pdf"
OUT_MD = ROOT / "RELATORIO_TECNICO.md"



def ensure_pdf_reader():
    import importlib
    import importlib.util
    import sys

    candidates = ["pypdf", "PyPDF2", "pypdf2"]
    for name in candidates:
        try:
            spec = importlib.util.find_spec(name)
            if spec is not None:
                mod = importlib.import_module(name)
                return mod
        except Exception:
            continue

    # not found: return None but include diagnostics in caller
    return None


def simple_structure_text(raw_text: str) -> str:
    # Heurística simples para transformar texto plano em Markdown:
    # - linhas em MAIÚSCULAS curtas -> Heading
    # - separa páginas com '---'
    lines = [l.rstrip() for l in raw_text.splitlines()]
    out_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
        # heading heuristic: all letters (ignoring digits/punct) uppercase and short
        letters = [c for c in s if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and len(s) < 80:
            out_lines.append("# " + s)
        else:
            out_lines.append(s)
    return "\n".join(out_lines)


def main() -> int:
    if not PDF_FILE.exists():
        print(f"Arquivo PDF não encontrado: {PDF_FILE}")
        return 2

    pdf_module = ensure_pdf_reader()
    if pdf_module is None:
        import sys
        import importlib.util

        print("Biblioteca 'pypdf' (ou PyPDF2) não encontrada. Tente instalar com: python -m pip install pypdf")
        print("Diagnóstico:")
        print(" Python executable:", sys.executable)
        print(" sys.path:")
        for p in sys.path:
            print("  ", p)
        print("find_spec('pypdf'):", importlib.util.find_spec("pypdf"))
        print("find_spec('PyPDF2'):", importlib.util.find_spec("PyPDF2"))
        return 3

    # carregar e extrair
    try:
        reader = pdf_module.PdfReader(str(PDF_FILE))
    except Exception as exc:
        print(f"Erro ao abrir PDF: {exc}")
        return 4

    pages_text = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            # compat PyPDF2 older
            try:
                text = page.extractText() or ""
            except Exception:
                text = ""
        pages_text.append(text)

    if not any(pages_text):
        print("Nenhum texto extraído do PDF.")
        return 5

    # montar markdown
    md_parts = []
    for i, pt in enumerate(pages_text):
        md = simple_structure_text(pt)
        md_parts.append(md)
        if i != len(pages_text) - 1:
            md_parts.append("\n\n---\n\n")

    OUT_MD.write_text("\n".join(md_parts), encoding="utf-8")
    print(f"Markdown gerado em: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
