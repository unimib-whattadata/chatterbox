#!/usr/bin/env python3
"""
Simple tester for POST /v1/text-to-speech/{voice_id}.

Example:
  # Use env var for API key
  export CHATTERBOX_API_KEY=your_key_here
  python chatterbox/scripts/test_text_to_speech.py --voice my_voice --text "Hello world"

  # Or pass API key on CLI
  python chatterbox/scripts/test_text_to_speech.py --voice my_voice --text "Hello" --api-key your_key_here

The script will write the response audio to --output (default: out.wav).
"""
import os
import sys
import argparse
import json
from typing import Optional

import requests

def build_request_body(text: str,
                       model_id: Optional[str],
                       language_code: Optional[str],
                       stability: Optional[float],
                       similarity_boost: Optional[float],
                       style: Optional[float],
                       use_speaker_boost: Optional[bool]):
    body = {"text": text}
    if model_id is not None:
        body["model_id"] = model_id
    if language_code is not None:
        body["language_code"] = language_code

    # Build voice_settings only if any provided
    vs = {}
    if stability is not None:
        vs["stability"] = stability
    if similarity_boost is not None:
        vs["similarity_boost"] = similarity_boost
    if style is not None:
        vs["style"] = style
    if use_speaker_boost is not None:
        vs["use_speaker_boost"] = use_speaker_boost

    if vs:
        body["voice_settings"] = vs

    return body

def main():
    parser = argparse.ArgumentParser(description="Test /v1/text-to-speech/{voice_id}")
    parser.add_argument("--server", "-s", default="http://127.0.0.1:8000",
                        help="Base URL of the running API (default: http://127.0.0.1:8000)")
    parser.add_argument("--voice", "-v", required=True, help="voice_id path parameter (or path to audio prompt file)")
    parser.add_argument("--text", "-t", required=True, help="Text to synthesize")
    parser.add_argument("--api-key", "-k", default=None, help="xi-api-key header (falls back to CHATTERBOX_API_KEY env var)")
    parser.add_argument("--output", "-o", default="out.wav", help="Output WAV filename")
    parser.add_argument("--model-id", help="Optional model_id (default on server is 'chatterbox_turbo')")
    parser.add_argument("--language-code", help="Optional language_code")
    parser.add_argument("--stability", type=float, help="Optional voice_settings.stability (0..1)")
    parser.add_argument("--similarity-boost", type=float, help="Optional voice_settings.similarity_boost (0..1)")
    parser.add_argument("--style", type=float, help="Optional voice_settings.style (exaggeration)")
    parser.add_argument("--use-speaker-boost", type=lambda s: s.lower() in ("1","true","yes"), nargs='?', const=True,
                        help="Optional voice_settings.use_speaker_boost (true/false). Pass flag to enable; use --use-speaker-boost false to set false.")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("CHATTERBOX_API_KEY")
    if not api_key:
        print("Error: API key not supplied. Set CHATTERBOX_API_KEY env var or pass --api-key.", file=sys.stderr)
        sys.exit(2)

    body = build_request_body(
        text=args.text,
        model_id=args.model_id,
        language_code=args.language_code,
        stability=args.stability,
        similarity_boost=args.similarity_boost,
        style=args.style,
        use_speaker_boost=args.use_speaker_boost
    )

    url = f"{args.server.rstrip('/')}/v1/text-to-speech/{args.voice}"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/wav",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=args.timeout)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(3)

    if resp.status_code == 200:
        content_type = resp.headers.get("Content-Type", "")
        # Accept audio responses; server uses audio/wav for success
        if "audio" in content_type or "wav" in content_type:
            with open(args.output, "wb") as f:
                f.write(resp.content)
            print(f"Saved audio to {args.output} ({len(resp.content)} bytes).")
            sys.exit(0)
        else:
            # Unexpected but print body for debugging
            print("Received 200 but content-type is not audio. Headers:", resp.headers)
            print("Body:", resp.text)
            sys.exit(4)
    else:
        # Print error details returned by FastAPI
        print(f"Server returned status {resp.status_code}", file=sys.stderr)
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                print(json.dumps(resp.json(), indent=2), file=sys.stderr)
            except Exception:
                print(resp.text, file=sys.stderr)
        else:
            print(resp.text, file=sys.stderr)
        sys.exit(5)

if __name__ == "__main__":
    main()
