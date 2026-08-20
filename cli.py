"""Simple CLI for the Voltano RAG answer-generation layer.

Usage:
    python cli.py "Mennyi időn belül kell visszakapcsolni a fogyasztót az MVM Démásznál?"
    python cli.py            # interactive prompt loop
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from src.answer import answer_question
from src.config import check_env

CONFIDENCE_ICON = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def print_result(result) -> None:
    if result.status == "needs_clarification":
        print(f"[VISSZAKÉRDEZÉS] {result.message}\n")
        return
    icon = CONFIDENCE_ICON.get(result.confidence, "")
    label = result.provider or "(nem szolgáltatófüggő)"
    print(f"{icon} [{label}]")
    print(result.answer)
    if result.sources:
        print("\nForrások:")
        for s in result.sources:
            print(f"  - {s}")
    print()


def main() -> None:
    check_env()
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print_result(answer_question(query))
        return

    print("Voltano RAG - kérdezz (üres sor / Ctrl+C a kilépéshez):\n")
    try:
        while True:
            query = input("> ").strip()
            if not query:
                break
            print_result(answer_question(query))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
