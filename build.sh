#!/usr/bin/env bash
set -euo pipefail

start_ns=$(date +%s%N)
BUILD_MODE=false
trap 'if [ "$BUILD_MODE" = true ]; then elapsed_ns=$(date +%s%N); elapsed_cs=$(( (elapsed_ns - start_ns) / 10000000 )); elapsed_s=$(( elapsed_cs / 100 )); elapsed_cs_rem=$(( elapsed_cs % 100 )); echo "Took ${elapsed_s}.${elapsed_cs_rem}s"; fi' EXIT

# ── Paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_NAME="$(basename "$SCRIPT_DIR")"
ARDUINO_DIR="$SCRIPT_DIR/arduino"
BIN_DIR="$ARDUINO_DIR/bin"
BUILD_DIR="$SCRIPT_DIR/.build"

CLI="$BIN_DIR/arduino-cli"
if [ ! -x "$CLI" ]; then
    bash "$SCRIPT_DIR/setup_arduino.sh"
fi

if [ ! -f "$ARDUINO_DIR/env.sh" ]; then
    echo "Arduino environment not found.";
    exit 1
fi

source "$ARDUINO_DIR/env.sh"


# ── Commands ──────────────────────────────────────────────────────────
cmd_build() {
    mkdir -p "$BUILD_DIR"

    local SKETCH_DIR="$BUILD_DIR/$PROJ_NAME"
    mkdir -p "$SKETCH_DIR"
    cp "$SCRIPT_DIR/$PROJ_NAME.ino" "$SKETCH_DIR/$PROJ_NAME.ino"
    cp "$SCRIPT_DIR"/*.h "$SKETCH_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR"/*.cpp "$SKETCH_DIR/" 2>/dev/null || true
    for d in "$SCRIPT_DIR"/*/; do
        [ -d "$d" ] && cp -r "$d" "$SKETCH_DIR/"
    done

    "$CLI" compile \
        -b arduino:avr:nano \
        --output-dir "$BUILD_DIR" \
        --export-binaries \
        --jobs 0 \
        "$SKETCH_DIR" 2>&1

    local elf="$BUILD_DIR/$PROJ_NAME.ino.elf"
    local hex="$BUILD_DIR/$PROJ_NAME.ino.hex"

    if [ ! -f "$elf" ]; then
        echo "!!! WARNING: ELF file not found at $elf"
        return 1
    fi

    echo "  ELF:  $elf"
    [ -f "$hex" ] && echo "  HEX:  $hex"

    echo ""
    echo "Binary size:"
    avr-size "$elf"
}

# ── Main ──────────────────────────────────────────────────────────────
usage() {
    echo "Usage: ./build.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build              Compile locally (default)"
    echo "  help               Show this help"
    echo ""
    echo "Examples:"
    echo "  ./build.sh         # Build locally (installs Arduino CLI if needed)"
}

case "${1:-build}" in
    build)
        BUILD_MODE=true
        cmd_build
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "!!! WARNING: Unknown command: $1"
        usage
        exit 1
        ;;
esac
