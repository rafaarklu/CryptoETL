from __future__ import annotations

from pathlib import Path
import re

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, ListFlowable, ListItem, Paragraph, Preformatted, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILE = ROOT / "RELATORIO_TECNICO.md"
OUTPUT_FILE = ROOT / "RELATORIO_TECNICO.pdf"


def add_inline_styles(text: str) -> str:
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)

    parts = text.split("`")
    if len(parts) == 1:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    rendered = []
    for index, part in enumerate(parts):
        if index % 2 == 0:
            rendered.append(
                part.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
        else:
            rendered.append(f"<font name='Courier'>{part}</font>")
    return "".join(rendered)


def markdown_to_story(markdown: str):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Heading1Center", parent=styles["Heading1"], alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], leading=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="CodeBlock", parent=styles["Code"], fontName="Courier", fontSize=8, leading=10, leftIndent=8, spaceBefore=4, spaceAfter=8))

    story = []
    lines = markdown.splitlines()
    in_code = False
    code_lines = []
    bullet_items = []

    def flush_bullets() -> None:
        nonlocal bullet_items
        if not bullet_items:
            return

        story.append(
            ListFlowable(
                [ListItem(Paragraph(add_inline_styles(item), styles["Body"])) for item in bullet_items],
                bulletType="bullet",
                start="disc",
                leftIndent=16,
            )
        )
        story.append(Spacer(1, 4))
        bullet_items = []

    def flush_code() -> None:
        if not code_lines:
            return

        code_text = "\n".join(code_lines)
        story.append(Preformatted(code_text, styles["CodeBlock"]))
        story.append(Spacer(1, 6))

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                flush_code()
                code_lines = []
                in_code = False
            else:
                flush_bullets()
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        if line.startswith(("- ", "• ")):
            bullet_items.append(line[2:])
            continue

        flush_bullets()

        if not line.strip():
            flush_bullets()
            story.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:].strip(), styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), styles["Heading1Center"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), styles["Heading2"]))
        elif line.startswith("#### "):
            story.append(Paragraph(line[5:].strip(), styles["Heading3"]))
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(f"<b>{add_inline_styles(line.strip('*'))}</b>", styles["Body"]))
        elif line.startswith("!"):
            match = re.search(r"!\[(.*?)\]\((.*?)\)", line)
            if match:
                image_path = ROOT / match.group(2)
                if image_path.exists():
                    story.append(Image(str(image_path), width=16 * cm, height=9 * cm))
                    story.append(Spacer(1, 6))
        elif line == "---":
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(add_inline_styles(line), styles["Body"]))

    flush_bullets()
    flush_code()
    return story


def main() -> None:
    if not MARKDOWN_FILE.exists():
        # Fallback: gerar PDF simples listando evidências se o Markdown não existir
        print(f"Aviso: {MARKDOWN_FILE} não encontrado. Gerando PDF de evidência reduzido.")
        doc = SimpleDocTemplate(
            str(OUTPUT_FILE),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        story = [Paragraph("RELATÓRIO TÉCNICO - MARKDOWN NÃO ENCONTRADO", styles["Title"]), Spacer(1, 12)]
        story.append(Paragraph("O arquivo RELATORIO_TECNICO.md não foi encontrado no repositório. Abaixo segue a lista de evidências presentes em reports/screenshots/:", styles["BodyText"]))
        story.append(Spacer(1, 8))
        evidences = []
        evid_path = ROOT / "reports" / "screenshots"
        if evid_path.exists():
            for p in sorted(evid_path.iterdir()):
                evidences.append(str(p.relative_to(ROOT)))

        if evidences:
            for e in evidences:
                story.append(Paragraph(f"- {e}", styles["BodyText"]))
        else:
            story.append(Paragraph("(nenhuma evidência encontrada em reports/screenshots)", styles["BodyText"]))

        doc.build(story)
        print(f"PDF de evidência gerado em: {OUTPUT_FILE}")
        return

    try:
        markdown = MARKDOWN_FILE.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Erro ao ler {MARKDOWN_FILE}: {exc}")
        return

    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = markdown_to_story(markdown)
    doc.build(story)
    print(f"PDF gerado em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
