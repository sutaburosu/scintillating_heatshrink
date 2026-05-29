#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARDUINO_DIR="$SCRIPT_DIR/arduino"
BIN_DIR="$ARDUINO_DIR/bin"
DATA_DIR="$ARDUINO_DIR/data"
LIB_DIR="$DATA_DIR/libraries"
CONFIG_DIR="$ARDUINO_DIR"

# arduino-cli helper: runs cli with correct config dir
cli() {
    "$BIN_DIR/arduino-cli" --config-dir "$CONFIG_DIR" "$@"
}

echo "=== Arduino + AVR Toolchain Setup ==="
echo "Installing to: $ARDUINO_DIR"

# ── 1. Install arduino-cli ──────────────────────────────────────────
CLI="$BIN_DIR/arduino-cli"
if [ -x "$CLI" ]; then
    echo "arduino-cli already installed: $(cli version | head -1)"
else
    echo "Installing arduino-cli..."
    mkdir -p "$BIN_DIR"
    CLI_VERSION="$(curl -s https://api.github.com/repos/arduino/arduino-cli/releases/latest | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'].lstrip('v'))")"
    curl -fsSL "https://github.com/arduino/arduino-cli/releases/download/v${CLI_VERSION}/arduino-cli_${CLI_VERSION}_Linux_64bit.tar.gz" \
        -o "$BIN_DIR/arduino-cli.tar.gz"
    tar -xzf "$BIN_DIR/arduino-cli.tar.gz" -C "$BIN_DIR"
    rm "$BIN_DIR/arduino-cli.tar.gz"
    chmod +x "$CLI"
    cli version
fi

# ── 2. Configure arduino-cli ────────────────────────────────────────
cli config set board_manager.additional_urls "https://downloads.arduino.cc/packages/package_index.json"
cli config set directories.data "$DATA_DIR"

# ── 3. Install AVR core ─────────────────────────────────────────────
echo "Installing AVR core..."
cli core update-index
cli core upgrade
cli core install arduino:avr

# ── 4. Install FastLED ──────────────────────────────────────────────
echo "Installing FastLED library..."
cli lib install FastLED

# ── 5. Locate AVR toolchain ─────────────────────────────────────────
AVR_GCC_PARENT=$(find "$DATA_DIR"/packages/arduino/tools/avr-gcc -maxdepth 1 -type d 2>/dev/null | head -1)
AVR_GCC_DIR="$AVR_GCC_PARENT/$(ls "$AVR_GCC_PARENT" 2>/dev/null | head -1)"

if [ -z "$AVR_GCC_DIR" ]; then
    echo "ERROR: Could not find AVR toolchain in $DATA_DIR"
    exit 1
fi

AVR_BIN="$AVR_GCC_DIR/bin"
echo "AVR toolchain found at: $AVR_BIN"

# ── 6. Write helper script for PATH setup ───────────────────────────
cat > "$ARDUINO_DIR/env.sh" <<'ENV_EOF'
#!/usr/bin/env bash
# Source this file to add Arduino AVR tools to your PATH:
#   source arduino/env.sh

ARDUINO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find the avr-gcc version directory
AVR_GCC_BIN="$ARDUINO_DIR/data/packages/arduino/tools/avr-gcc/$(ls "$ARDUINO_DIR/data/packages/arduino/tools/avr-gcc" 2>/dev/null | head -1)/bin"
AVRDUDE_BIN="$ARDUINO_DIR/data/packages/arduino/tools/avrdude/$(ls "$ARDUINO_DIR/data/packages/arduino/tools/avrdude" 2>/dev/null | head -1)/bin"

export PATH="$ARDUINO_DIR/bin:$AVR_GCC_BIN:$AVRDUDE_BIN:$PATH"
ENV_EOF
chmod +x "$ARDUINO_DIR/env.sh"

# ── 7. Verification ─────────────────────────────────────────────────
# Prepend AVR tools to PATH for this session
AVRDUDE_BIN=$(find "$DATA_DIR/packages/arduino/tools/avrdude" -maxdepth 2 -name bin -type d 2>/dev/null | head -1)
export PATH="$AVR_BIN:$AVRDUDE_BIN:$BIN_DIR:$PATH"

echo ""
echo "=== Setup Summary ==="
echo "arduino-cli:  $(cli version | head -1)"
echo "AVR core:     $(cli core list 2>/dev/null | grep arduino:avr || echo '?')"
echo "FastLED:      $(cli lib list 2>/dev/null | grep FastLED || echo '?')"
echo ""
echo "AVR tools:"
echo "  avr-gcc:     $(avr-gcc --version | head -1)"
echo "  avr-objdump: $(avr-objdump --version | head -1)"
echo "  avr-size:    $(avr-size --version | head -1)"
echo "  avr-nm:      $(avr-nm --version | head -1)"
AVRDUDE_CONF=$(find "$DATA_DIR/packages/arduino/tools/avrdude" -name "avrdude.conf" 2>/dev/null | head -1)
avrdude -C "$AVRDUDE_CONF" -v > /tmp/_avrdude_ver.txt 2>&1 || true
AVRDUDE_VER=$(head -2 /tmp/_avrdude_ver.txt | tail -1)
rm -f /tmp/_avrdude_ver.txt
echo "  avrdude:     $AVRDUDE_VER"
echo ""
echo "To use in your shell, run:"
echo "  source arduino/env.sh"
echo ""
echo "=== Done ==="
