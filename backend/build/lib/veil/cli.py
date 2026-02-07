import argparse
from .compiler import compile_p0, compile_all

def main():
    parser = argparse.ArgumentParser(description="Veil OS Organ Engine")
    parser.add_argument("command", choices=["compile", "compile-p0"])
    args = parser.parse_args()

    if args.command == "compile":
        compile_all()
    elif args.command == "compile-p0":
        compile_p0()
