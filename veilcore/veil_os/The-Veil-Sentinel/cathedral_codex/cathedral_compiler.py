from flask import Flask, send_file, render_template_string
from markdown import markdown
from pathlib import Path
import weasyprint
import re

# Configuration
REPO_URL = "https://raw.githubusercontent.com/The-Fruit-Fly/The-Veil---Sentinel/main"
CODEX_DIR = Path("cathedral_codex")
SEALS_DIR = CODEX_DIR / "seals"
CHAPTERS = [
    "glyph-doctrine.md",
    "override-authority.md",
    "encryption-canon.md",
    "accessibility-oaths.md",
    "deployment-psalms.md",
    "emergence-protocols.md",
    "seal-registry.md"
]

app = Flask(__name__)

def autolink_images(md_text: str) -> str:
    """Convert ![](seals/image.png) to full raw GitHub URLs."""
    pattern = r'!\[(.*?)\]\(seals\/(.*?)\)'
    return re.sub(pattern, 
        lambda m: f"<img src='{REPO_URL}/cathedral_codex/seals/{m.group(2)}' alt='{m.group(1)}' width='200'/>",
        md_text
    )

def compile_codex_html() -> str:
    content = ""
    for name in CHAPTERS:
        path = CODEX_DIR / name
        if path.exists():
            md_raw = path.read_text(encoding="utf-8")
            md_processed = autolink_images(md_raw)
            html = markdown(md_processed)
            title = name.replace("-", " ").replace(".md", "").title()
            content += f"<h2>{title}</h2>\n{html}\n<hr/>\n"
        else:
            content += f"<h2>{name}</h2>\n<p><em>Missing</em></p><hr/>\n"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset='UTF-8'><title>The Veil Cathedral Codex</title></head>
    <body style='font-family:serif; padding:2em; max-width:800px; margin:auto;'>
    <h1>The Veil 🛡️ Cathedral Codex</h1>
    {content}
    </body>
    </html>
    """

@app.route("/codex")
def serve_html():
    html = compile_codex_html()
    return render_template_string(html)

@app.route("/codex/pdf")
def serve_pdf():
    html = compile_codex_html()
    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    pdf_path = CODEX_DIR / "Cathedral_Codex.pdf"
    pdf_path.write_bytes(pdf_bytes)
    return send_file(str(pdf_path), download_name="Cathedral_Codex.pdf")

if __name__ == "__main__":
    app.run(debug=True)
