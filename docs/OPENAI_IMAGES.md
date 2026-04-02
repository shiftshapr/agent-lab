# OpenAI DALL-E Image Generation

Generate images using your OpenAI account (DALL-E 3).

## Setup

1. Get an API key from [platform.openai.com](https://platform.openai.com/api-keys)
2. Add to `.env`:
   ```
   OPENAI_IMAGE_API_KEY=sk-...
   ```

## Usage

**CLI:**
```bash
.venv/bin/python scripts/generate-image-dalle.py "A sunset over mountains"
.venv/bin/python scripts/generate-image-dalle.py "Futuristic city" --output images/city.png --size 1792x1024 --quality hd
```

**Via Telegram/Shiftshapr:** Ask "Generate an image of [description]" — the agent can run the script when it has shell access.

**Options:**
- `--size`: 1024x1024 (default), 1792x1024 (landscape), 1024x1792 (portrait)
- `--quality`: standard (default) or hd
- `--style`: vivid (default) or natural

Output goes to `data/outputs/dalle_<timestamp>.png` unless `--output` is set.
