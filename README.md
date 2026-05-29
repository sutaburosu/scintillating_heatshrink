# scintillating_heatshrink

Plays heatshrink-compressed GIF animations on a 16x16 WS2812B LED matrix driven by an Arduino Nano.

Two effects run in parallel: a rainbow smoothie color pattern and decompressed sprite animations that crossfade over it. Sprites rotate every 2.5 seconds.

## Hardware

- Arduino Nano (ATmega328P)
- 16x16 WS2812B (NeoPixel) LED matrix

## Quick Start

```bash
./build.sh          # compile (installs arduino-cli and AVR toolchain if needed)
```

The compiled HEX is written to `.build/scintillating_heatshrink.ino.hex`. Upload it to the Arduino using your preferred method.

## Adding Animations

Convert a GIF (must be 16x16) to a C header:

```bash
python3 gif2h.py my_animation.gif
```

This generates `my_animation.h` in the current directory. Copy it into `GIF/`, add an `#include` line to `hsprites.h`, and add it to the playlist `hsprite_list[]`. The animation will be included in the build.

## Previewing Animations

A PyQt6 GUI viewer reconstructs sprites from header files and displays them alongside the source GIF:

```bash
python3 view_sprites.py                   # all GIF/*.h files
python3 view_sprites.py GIF/owl.h GIF/fire.h   # specific files
```

Keyboard shortcuts:
- **Space** — play/pause
- **Left/Right** — previous/next animation
- **PgUp/PgDn** — previous/next frame
- **+/-** or **mouse wheel** — zoom

## Serial Controls

Connect to the Arduino at 250000 baud. Available commands:

| Key | Action |
|-----|--------|
| `e` | Next effect |
| `p` | Next palette |
| `b` / `B` | Brightness down / up |
| `f` / `F` | Fade rate down / up |
| `~` | Next rainbow smoothie preset |
| `, . < >` | Adjust colour cycling rate |
| `#` | Randomise rainbow smoothie |
| **Enter** | Print parameters |



## Reddit Discussion

See the [original Reddit announcement post](https://www.reddit.com/r/FastLED/comments/gt31y4/playing_gif_animations_on_avr/) for this project.


## AI Disclosure

When this repo was published in 2020, it was 100% human effort: mine alone. The libraries, and languages used in this project have moved on, so in 2026 I updated it to work with the current versions of old dependencies: Python, Pillow, and FastLED. For a project this old and unattended, I could never muster the effort to update it all manually, so I used AI to help with the updates. I estimate the AI contribution to be as follows:

| File | AI contribution estimate | 
|------|-----------------------------|
| `scintillating_heatshrink.ino` | <1% |
| `README.md` | ~10% |
| `gif2h.py` | ~50% |
| `view_sprites.py` | 100% |
| `build.sh` | 100% |
| `heatshrink_python` | 100% |

I used local AI exclusively: [llama.cpp](https://github.com/ggerganov/llama.cpp) running [unsloth/Qwen3.6-35B-A3B-MTP-GGUF:Q8_K_XL](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF), using [opencode.ai](https://opencode.ai) as the harness. The harness ran within a local VM to mitigate regrettable actions. The exact command I launched llama.ccp with was:

```bash
./llama-server -hf unsloth/Qwen3.6-35B-A3B-MTP-GGUF:Q8_K_XL --fit on -c 262144 --flash-attn on --swa-full -np 1 --spec-type draft-mtp --spec-draft-n-max 2 --chat-template-kwargs '{preserve_thinking:true}'  --temp 0.6 --top-p 0.95 --top-k 20 --presence-penalty 0.0 --min-p 0.0 --no-mmproj
```

No cloud compute was used. Everything ran locally on my desktop computer: a Ryzen 9 7950X with 64GiB RAM, plus an Radeon RX 7800XT (16GiB VRAM). There was a 16GiB swapfile which was barely used. The mean increase in power consumption over my baseline desktop usage was ~100W. Depending on how much of the 262,144-token context window was active, it encoded at ~180-90 tokens per second, and decoded at ~40-20 tokens per second. Over 1-million tokens were processed in porting the heatshrink C library to Python alone.

## Acknowledgements

- [heatshrink](https://github.com/atomicobject/heatshrink) by Scott Vokes
- [FastLED](http://fastled.io/)

