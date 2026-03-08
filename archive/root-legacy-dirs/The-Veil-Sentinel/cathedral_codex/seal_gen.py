import svgwrite
from pathlib import Path

# Define seal glyphs and meanings
seals = {
    "emergency": {"glyph": "🜁", "title": "Emergency Override", "color": "#FF3B3B"},
    "flame":     {"glyph": "🜂", "title": "Time-Sensitive Escalation", "color": "#FF8C00"},
    "earth":     {"glyph": "🜃", "title": "Persistent Sovereignty", "color": "#228B22"},
    "audit":     {"glyph": "🜄", "title": "Audit Transparency", "color": "#4169E1"},
    "ether":     {"glyph": "🜅", "title": "Seal Invocation", "color": "#6A5ACD"}
}

# Output folder
output_dir = Path("cathedral_codex/seals")
output_dir.mkdir(parents=True, exist_ok=True)

def create_seal(name, glyph, title, color):
    dwg = svgwrite.Drawing(str(output_dir / f"{name}.svg"), size=("200px", "200px"))
    dwg.add(dwg.rect(insert=(0, 0), size=("200px", "200px"), fill=color, rx=20, ry=20))
    dwg.add(dwg.text(glyph, insert=("100px", "110px"), text_anchor="middle",
                     font_size="80px", fill="white", font_family="serif"))
    dwg.add(dwg.text(title, insert=("100px", "190px"), text_anchor="middle",
                     font_size="14px", fill="white"))
    dwg.save()

# Generate each seal
for name, spec in seals.items():
    create_seal(name, spec["glyph"], spec["title"], spec["color"])

print("✅ Seal set generated to cathedral_codex/seals/")
