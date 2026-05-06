"""Command entrypoint for `python -m Core.midnight.semantic`."""

import json

from . import run_semantic_assembly


if __name__ == "__main__":
    packet = run_semantic_assembly()
    print(
        json.dumps(
            {
                "status": packet.get("status"),
                "axis": packet.get("axis"),
                "branch_count": len(packet.get("self", {}).get("branch_specs", []) or []),
            },
            ensure_ascii=False,
        )
    )
