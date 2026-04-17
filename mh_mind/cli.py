import argparse
import sys


def cmd_sync(args: argparse.Namespace) -> int:
    print("sync: not implemented")
    return 1


def cmd_chat(args: argparse.Namespace) -> int:
    print("chat: not implemented (run `streamlit run app.py` instead)")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mh-mind")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="Ingest Apple Notes and Word docs into the local corpus.")
    sub.add_parser("chat", help="Chat with your notes in the terminal.")

    args = parser.parse_args(argv)
    handlers = {"sync": cmd_sync, "chat": cmd_chat}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
