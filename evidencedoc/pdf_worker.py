"""Disposable Linux parser: hard memory/CPU limits before importing PDF libraries."""

import json
import sys


def main():
    if not sys.platform.startswith("linux"):
        print(
            json.dumps(
                {
                    "error": "Resource-limited PDF processing requires Linux. Use the Docker image on other systems."
                }
            )
        )
        return
    import resource

    memory = 768 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    from dataclasses import asdict

    from evidencedoc.documents import MAX_BYTES, extract_pages

    try:
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("The PDF must be 10 MB or smaller.")
        pages, skipped = extract_pages(data)
        print(json.dumps({"pages": [asdict(page) for page in pages], "skipped_pages": skipped}))
    except (MemoryError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc)
                    if isinstance(exc, ValueError)
                    else "The PDF exceeded the memory limit."
                }
            )
        )


if __name__ == "__main__":
    main()
