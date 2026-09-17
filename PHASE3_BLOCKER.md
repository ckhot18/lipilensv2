# Phase 3 blocker: model weights won't download (read this first)

## The problem (one paragraph)
The code is fine. The machine is fine. The ~7 GB download of the Qwen2.5-VL-3B
model weights from Hugging Face stalls at 0% and never finishes: a 30-minute
attempt moved ~810 MB across the wire but completed almost nothing, because
roughly 3 out of every 4 data chunks fail and get retried in an endless loop.
Small requests (model info, configs) take <1 second, so this is specifically
the big-file download pipe that is broken, not "the internet" as a whole.

## Proof (all observed, not guessed)
- HF API call: 0.54 s — small-file path is healthy.
- Cache after 30 min: only 16.8 MB of small files; zero weight shards.
- XET downloader log (`D:\hf_cache\xet\logs\...4292.log`): repeats
  "connection struggling (success_ratio = 0.23–0.25)" hundreds of times,
  concurrency forced down to 1, predicted bandwidth ~24 KB/s,
  810,940,603 bytes "sent" for only 92 completed transmissions.
- Our requests are UNauthenticated (Hub prints a rate-limit warning every run),
  which puts us in the lowest download-priority tier.

## What YOU can do (easiest first, ~10 min total)
1. **Log in to Hugging Face (highest chance of fixing it, 2 min).**
   Create a free account at huggingface.co/join, then Profile photo >
   Access Tokens > Create token (type: Read). Then in a terminal:
     cd D:\Projects\lipilensv2
     .\.venv\Scripts\python.exe -m huggingface_hub.commands.huggingface_cli login
   Paste the token. Authenticated users get far better download priority.
2. **Run the resume download yourself (don't do it through me).**
     cd D:\Projects\lipilensv2
     .\.venv\Scripts\python.exe scripts\download_model.py
   It resumes where it stopped, shows a real progress bar, and uses
   `D:\hf_cache` automatically (C: has only ~4.4 GB free — never use C:).
   If it stalls again, stop it (Ctrl+C) and retry with:
     .\.venv\Scripts\python.exe scripts\download_model.py --no-xet
   Just send me the last 10 lines if it fails.
3. **2-minute hotspot test (tells us if your ISP is the culprit).**
   Connect the PC to your phone's mobile data and re-run step 2 for 2 minutes.
   Fast = home broadband route to Hugging Face's file server is bad (then just
   finish the download on hotspot, or use option 4). Slow = it's the HF side
   or the PC, not your ISP.
4. **Skip the download entirely (zero bytes, ~15 min).**
   Open `colab/lipilens_colab_server.py`, follow the 5-line instructions at the
   top in a free Colab GPU notebook, and paste the ngrok URL back to me as
   `COLAB_ENDPOINT_URL`. Google downloads the weights in ~2 minutes on their
   own network. This is the project's official fallback plan anyway.

## Please don't
- Don't ask me to "retry the download" — each blind retry burns ~30 min and
  thousands of tokens for the same 24 KB/s trickle. Run step 2 yourself and
  paste me the output.
- Don't delete `D:\hf_cache` — partial files there are resumable and save time.
