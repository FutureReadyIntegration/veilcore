#!/usr/bin/env python3
import argparse, re
from pathlib import Path

def ensure_deps():
    try:
        import cairosvg  # noqa
        from PIL import Image  # noqa
    except Exception as e:
        raise SystemExit(
            "\nERROR: Missing deps for GIF rebuild.\n"
            "Install (prefer your venv if you have one):\n"
            "  python3 -m pip install --upgrade pip\n"
            "  python3 -m pip install cairosvg pillow\n\n"
            f"Original error: {e}\n"
        )

def main():
    ensure_deps()
    import cairosvg
    from PIL import Image
    import io

    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--gif", required=True)
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--duration", type=float, default=0.06)
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=900)
    args = ap.parse_args()

    svg_path = Path(args.svg)
    gif_path = Path(args.gif)
    svg = svg_path.read_text(encoding="utf-8")

    # Freeze an existing sweep animation per-frame if present (your previous pattern)
    # If not found, renders static frames (still produces a GIF).
    use_exact = 'values="-1200;-400;800"' in svg
    sweep_pat = r'values="(-?\d+);(-?\d+);(-?\d+)"'
    m = re.search(sweep_pat, svg)

    frames = []
    N = max(2, args.frames)

    # Determine sweep range
    if use_exact:
        x_start, x_end = -1200.0, 800.0
    elif m:
        x_start, x_end = float(m.group(1)), float(m.group(3))
    else:
        x_start = x_end = 0.0

    for i in range(N):
        t = i / (N - 1)
        x = x_start + (x_end - x_start) * t
        s2 = svg
        if use_exact:
            s2 = s2.replace('values="-1200;-400;800"', f'values="{x};{x};{x}"')
        elif m:
            s2 = re.sub(sweep_pat, f'values="{x};{x};{x}"', s2, count=1)

        png = cairosvg.svg2png(bytestring=s2.encode("utf-8"),
                               output_width=args.width, output_height=args.height)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        frames.append(im)

    gif_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(args.duration * 1000),
        loop=0,
        disposal=2,
    )
    print(f"OK: wrote {gif_path}")

if __name__ == "__main__":
    main()
