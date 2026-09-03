"""CLI: python -m om_prime_adapter open_job <job_id> | compile_cut <job_id> <shot_id>"""

from __future__ import annotations

import argparse
import json
import sys

from . import compile_cut, open_job, run
from .adapter import AdapterError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prime → OM production adapter. Proposal only.")
    sub = parser.add_subparsers(dest="command", required=True)
    open_p = sub.add_parser("open_job")
    open_p.add_argument("job_id")
    compile_p = sub.add_parser("compile_cut")
    compile_p.add_argument("job_id")
    compile_p.add_argument("shot_id")
    compile_p.add_argument("--caller", default="prime")
    compile_p.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "open_job":
            payload = open_job(args.job_id)
        elif args.command == "compile_cut":
            payload = compile_cut(
                args.job_id,
                args.shot_id,
                caller=args.caller,
                write=not args.no_write,
            )
        else:
            payload = run(args.command)
    except AdapterError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
