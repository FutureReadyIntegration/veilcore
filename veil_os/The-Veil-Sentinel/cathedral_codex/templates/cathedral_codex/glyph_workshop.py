import svgwrite
from pathlib import Path
from typer import Typer

app = Typer()
output_dir = Path("cathedral_codex/seals")
output_dir.mkdir(parents=True, exist_ok=True)

@app.command()
def forge(
    glyph: str,
    title: str,
    filename: str,
    color: str = "#333333",
    text_color: str = "#FFFFFF"
):
    """Forge a new glyph-based seal."""
    dwg = svgwrite.Drawing(str(output_dir / filename), size=("200px", "200px"))
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "200px"), fill=color, rx=20, ry=20))
    dwg.add(dwg.text(glyph, insert=("100px", "110px"), text_anchor="middle",
                     font_size="80px", fill=text_color, font_family="serif"))
    dwg.add(dwg.text(title, insert=("100px", "190px"), text_anchor="middle",
                     font_size="14px", fill=text_color))
    dwg.save()
    print(f"✅ Seal saved to: {output_dir / filename}")

if __name__ == "__main__":
    app()
