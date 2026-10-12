"""End-to-end check of the exact path a live demo takes.

This is the test that matters before a showcase: it exercises the real API with
the real model on a real page, and asserts the claims the deck makes about the
demo (restoration preview is instant, progress is reported, transcription
completes). It is deliberately a script rather than a pytest case because it
needs the GPU, which no unit test may claim.
"""

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGE = ROOT / "showcase" / "images" / "MT-002.png"


def pick_image() -> pathlib.Path:
    """Pick a showcase page that is NOT already in the archive.

    Uploading a page that is already stored is idempotent: the API returns the
    existing record without running the model. That is correct behaviour, but
    it makes a rehearsal look instant and prove nothing, so this script
    deliberately avoids those pages.
    """
    if len(sys.argv) > 1:
        return ROOT / "showcase" / "images" / f"{sys.argv[1]}.png"
    return IMAGE


def post_multipart(path: str, fields: dict, file_field: str | None = None,
                   file_path: pathlib.Path | None = None) -> dict:
    boundary = "----lipilensdemo0123456789"
    body = bytearray()
    for k, v in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        body += f"{v}\r\n".encode()
    if file_field and file_path:
        body += f"--{boundary}\r\n".encode()
        body += (f'Content-Disposition: form-data; name="{file_field}"; '
                 f'filename="{file_path.name}"\r\n').encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += file_path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BASE}{path}", data=bytes(body), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def main() -> int:
    image = pick_image()
    if not image.exists():
        print(f"FAIL no showcase image at {image}")
        return 1
    print(f"image: {image.name}")

    health = get("/api/health")
    print(f"health: {health}")
    if health.get("status") != "ok":
        print("FAIL backend not healthy")
        return 1

    # 1. Restoration preview must be CPU-only and fast; the deck claims ~184 ms.
    t0 = time.perf_counter()
    prev = post_multipart("/api/manuscripts/preview", {"config_name": "enhanced"},
                          "file", image)
    dt = (time.perf_counter() - t0) * 1000
    print(f"preview: {json.dumps(prev, ensure_ascii=False)[:150]}")
    print(f"        wall {dt:.0f} ms")
    if dt > 3000:
        print("FAIL preview too slow to call instant in a demo")

    # 2. Upload with transcribe=false, which is the "clean it" act: restoration
    #    only, no model call. This is the two-step flow the deck describes.
    man = post_multipart("/api/manuscripts",
                         {"title": "SHOWCASE-SMOKE-TEST", "transcribe": "false"},
                         "file", image)
    mid = man["id"]
    print(f"uploaded: id={mid} title={man['title']!r} status={man['status']!r}")
    if man.get("duplicate"):
        # Uploading a page already in the archive is idempotent: the API returns
        # the stored record and never runs the model. A rehearsal that reuses a
        # page therefore returns instantly and demonstrates nothing.
        print(f"FAIL {image.name} is already in the archive (id={mid}). "
              f"Pick a different page, or delete the record first.")
        return 1
    if man["status"] != "restored":
        print(f"FAIL expected status 'restored' after a transcribe=false "
              f"upload, got {man['status']!r} - the model ran during upload")
        return 1
    if man["title"] != "SHOWCASE-SMOKE-TEST":
        print(f"FAIL title was not preserved: {man['title']!r}")
        return 1

    # 3. Kick off transcription and watch progress, as the UI does.
    t_start = time.perf_counter()
    post_multipart(f"/api/manuscripts/{mid}/transcribe", {})
    print("transcribe requested")

    stages, last, first_output_at = [], None, None
    deadline = time.time() + 900
    state = None
    while time.time() < deadline:
        p = get(f"/api/manuscripts/{mid}/progress")
        state = p.get("state") or p.get("stage")
        if state != last:
            stages.append(state)
            print(f"  stage: {state}  ({p.get('message', '')[:60]})  "
                  f"t+{time.perf_counter() - t_start:5.1f}s")
            last = state
        # First moment any text exists is what an audience perceives as
        # "it started working". On a cold model this is the 85 s load.
        if first_output_at is None and (p.get("partial_text") or "").strip():
            first_output_at = time.perf_counter() - t_start
        if state in ("done", "error", "failed"):
            break
        time.sleep(0.5)
    else:
        print("FAIL transcription did not finish within 900 s")
        return 1

    total = time.perf_counter() - t_start
    if first_output_at is not None:
        print(f"first output at t+{first_output_at:.1f}s")
    print(f"transcription complete at t+{total:.1f}s")

    detail = get(f"/api/manuscripts/{mid}")
    # `transcription` is a nested object; the text lives under ai_transcription.
    tr = detail.get("transcription") or {}
    text = (tr.get("ai_transcription") or "").strip()
    print(f"transcription: {len(text)} chars")
    print(f"  {text[:110]}")

    if state == "error" or not text:
        print("FAIL no transcription returned")
        return 1

    print(f"\nstages observed: {stages}")
    print("PASS live demo path works")
    print(f"note: manuscript {mid} is now in the library - delete it before a demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
