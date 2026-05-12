from __future__ import annotations

import argparse
import asyncio
import base64
import json
import time
from pathlib import Path

import websockets


async def run(url: str, image_path: Path, heading: float) -> None:
    payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    async with websockets.connect(url, max_size=10_000_000) as ws:
        msg = {
            "type": "frame",
            "timestamp_ms": int(time.time() * 1000),
            "jpeg_b64": payload,
            "heading_deg": heading,
        }
        await ws.send(json.dumps(msg))
        resp = await ws.recv()
        print(resp)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="ws://host:port/api/v1/session/<id>/stream")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--heading", default=0.0, type=float)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.image, args.heading))


if __name__ == "__main__":
    main()
