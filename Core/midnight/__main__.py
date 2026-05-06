"""Command entrypoint for `python -m Core.midnight`."""

import json

from . import run_night


if __name__ == "__main__":
    packet = run_night()
    print(
        json.dumps(
            {
                "status": packet.get("status"),
                "recent_unprocessed_count": packet.get("recent", {}).get("unprocessed_count"),
                "future_decision": packet.get("future", {}).get("decision", {}).get("decision"),
            },
            ensure_ascii=False,
        )
    )
