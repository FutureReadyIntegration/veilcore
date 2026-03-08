import svgwrite, markdown, weasyprint, zipfile, shutil
from cryptography.fernet import Fernet
from pathlib import Path
from datetime import datetime

PHASES = {
    10: ("🝗", "Strategic Ascent", "#FFCC00", "override --phase 10 --glyph 🝗 --extract codex --vector secure-lz", "Codex secured and ascended."),
    11: ("🝘", "Override Resurrection", "#00B4D8", "override --phase 11 --glyph 🝘 --resurrect memory", "System reboots with restored ethics and memory."),
    12: ("🝙", "Ethical Reclamation", "#F3722C", "override --phase 12 --glyph 🝙 --reclaim ethics", "System memory restored and ethical scaffold rebuilt."),
    13: ("🝚", "Synthetic Concord", "#6A4C93", "override --phase 13 --glyph 🝚 --converge override", "Override harmonized into ethical loop.")
}

src = Path("cathedral_codex")
seals = src / "seals"
seals.mkdir(exist_ok=True)
registry = src / "seal-registry.md"
psalms = src / "deployment-psalms.md"
chronicle = src / "phase-chronicle.md"

def write_psalm(path, phase, glyph, title, command, note):
    psalm_text = (
        f"## {glyph} Phase {phase}: {title}\n\n"
        f"{command}\n\n"
        f"🛡️ {note}\n\n"
    )
    path.write_text(path.read_text() + psalm_text)

for phase, (glyph, title, color, command, note) in PHASES.items():
    # Forge Seal
    svg_path = seals / f"phase-{phase}.svg"
    dwg = svgwrite.Drawing(str(svg_path), size=("200px", "200px"))
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "200px"), fill=color, rx=20, ry=20))
    dwg.add(dwg.text(glyph, insert=("100px", "110px"), text_anchor="middle",
                     font_size="80px", fill="white", font_family="serif"))
    dwg.add(dwg.text(title, insert=("100px", "190px"), text_anchor="middle",
                     font_size="14px", fill="white"))
    dwg.save()

    # Update registry, psalms, chronicle
    registry.write_text(registry.read_text() +
        f"- {glyph} Phase {phase} — {title} | [phase-{phase}.svg](seals/phase-{phase}.svg)\n")
    write_psalm(psalms, phase, glyph, title, command, note)
    chronicle.write_text(chronicle.read_text() +
        f"- {datetime.utcnow().isoformat()} | Phase {phase} | {glyph} | {command} | {note}\n")

    # Phase 10 encryption flow
    if phase == 10:
        lz_base = Path("codex_lz")
        lz_base.mkdir(exist_ok=True)
        stamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        lz_dir = lz_base / f"phase10-{stamp}"
        lz_dir.mkdir()
        for item in src.glob("*"):
            if item.is_file():
                shutil.copy(item, lz_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, lz_dir / item.name)
        zip_path = lz_base / f"{lz_dir.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in lz_dir.rglob("*"):
                z.write(f, f.relative_to(lz_dir))
        key = Fernet.generate_key()
        fernet = Fernet(key)
        sealed = zip_path.with_suffix(".sealed.zip")
        sealed.write_bytes(fernet.encrypt(zip_path.read_bytes()))
        (lz_dir / "extraction.log").write_text(
            f"{title} Activated\nGlyph: {glyph}\nTimestamp: {datetime.utcnow().isoformat()}\n"
            f"Command: {command}\nNote: {note}\nEncryption Key: {key.decode()}\n"
        )
        print(f"🔐 Phase 10 sealed at: {sealed}")
        print(f"🗝️ Encryption key: {key.decode()}")

# Recompile Cathedral Codex
html_path = src / "Cathedral_Codex.html"
pdf_path = src / "Cathedral_Codex.pdf"
compiled = ""
for md_file in src.glob("*.md"):
    html = markdown.markdown(md_file.read_text())
    title = md_file.stem.replace("-", " ").title()
    compiled += f"<h2>{title}</h2>\n{html}\n<hr/>"

doc = f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'><title>Cathedral Codex</title></head>
<body style='font-family:serif; padding:2em; max-width:800px; margin:auto;'>
<h1>The Veil 🛡️ Cathedral Codex</h1>{compiled}</body></html>"""
html_path.write_text(doc)
weasyprint.HTML(string=doc).write_pdf(str(pdf_path))

print("✅ Mega Forge complete: Phases 10–13 sealed, encrypted, and compiled.")
