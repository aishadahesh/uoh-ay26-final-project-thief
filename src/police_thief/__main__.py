"""Enables `uv run python -m police_thief <command>`.

This thief submission repo defaults `serve` to the thief role.
The PDF-compatible `peer --role police` command is also supported as an
alias for `serve --role cop`. Police/cop mode is only a local opponent-peer
test mode in this thief repo; see README.md.
"""

from police_thief.main import main

if __name__ == "__main__":
    main()
