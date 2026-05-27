#!/usr/bin/env python3
"""
Comprehensive test suite for Heatshrink encoder and decoder.

Tests cover:
- Byte-identical output to C reference implementation
- Correct decompression (roundtrip)
- Edge cases: empty input, single byte, repeated bytes, random data
- Various input sizes: small, window-sized, multi-window, large
- All values (0x00-0xFF), null bytes, 0xFF bytes
- Real-world-like patterns (repeating sequences, counter patterns)
"""

import sys
import os
import subprocess
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from heatshrink_encoder import compress, HeatshrinkEncoder
from heatshrink_decoder import decompress, HeatshrinkDecoder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compare_with_c(data: bytes, window_sz2: int = 8, lookahead_sz2: int = 7) -> bytes:
    """Compress *data* with C reference and return bytes."""
    result = subprocess.run(
        ["./heatshrink", "-w", str(window_sz2), "-l", str(lookahead_sz2)],
        input=data,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"C encoder failed: {result.stderr}"
    return result.stdout


def c_roundtrip(data: bytes, window_sz2: int = 8) -> bytes:
    """Compress with C encoder, decompress with C decoder, return result."""
    compressed = compare_with_c(data, window_sz2)
    result = subprocess.run(
        ["./heatshrink", "-d", "-w", str(window_sz2)],
        input=compressed,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"C decoder failed: {result.stderr}"
    return result.stdout


# ---------------------------------------------------------------------------
# 1. Encoder produces byte-identical output to C reference
# ---------------------------------------------------------------------------

class TestEncoderMatchesC:
    """Python encoder must produce byte-identical output to C encoder."""

    @pytest.mark.parametrize("data", [
        b"",
        b"A",
        b"AA",
        b"AAAA",
        b"A" * 10,
        b"A" * 63,
        b"A" * 64,
        b"A" * 65,
        b"A" * 100,
        b"A" * 127,
        b"A" * 128,
        b"A" * 129,
        b"A" * 200,
        b"A" * 255,
        b"A" * 256,
        b"A" * 257,
        b"A" * 512,
        b"A" * 1000,
        b"A" * 10000,
    ])
    def test_repeated_bytes(self, data):
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out, (
            f"Length mismatch: Python={len(py_out)} C={len(c_out)}\n"
            f"Python: {py_out.hex()}\nC:      {c_out.hex()}"
        )

    @pytest.mark.parametrize("data", [
        b"\x00",
        b"\x00" * 10,
        b"\x00" * 100,
        b"\x00" * 1000,
        b"\xff",
        b"\xff" * 10,
        b"\xff" * 100,
        b"\xff" * 1000,
    ])
    def test_extreme_bytes(self, data):
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.parametrize("data", [
        bytes(range(256)),
        bytes(range(256)) * 2,
        bytes(range(256)) * 4,
        bytes(range(128)) * 8,
        bytes(range(64)) * 16,
    ])
    def test_counter_patterns(self, data):
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.parametrize("data", [
        b"Hello, World!",
        b"Hello, World! Hello, World!",
        b"Hello, World!" * 20,
        b"The quick brown fox jumps over the lazy dog" * 5,
        b"abcdefghij" * 100,
    ])
    def test_text_patterns(self, data):
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out

    def test_random_data(self):
        import random
        random.seed(42)
        data = bytes(random.randint(0, 255) for _ in range(2000))
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.parametrize("window_sz2", [4, 5, 6, 7, 8, 9, 10, 12, 14])
    def test_different_window_sizes(self, window_sz2):
        data = b"ABCDEF" * 100
        lookahead_sz2 = window_sz2 - 1
        py_out = compress(data, window_sz2, lookahead_sz2)
        c_out = compare_with_c(data, window_sz2, lookahead_sz2)
        assert py_out == c_out


# ---------------------------------------------------------------------------
# 2. Decoder roundtrip — compressed data decompresses to original
# ---------------------------------------------------------------------------

class TestDecoderRoundtrip:
    """Compressed data must decompress to the exact original input."""

    @pytest.mark.parametrize("data", [
        b"",
        b"A",
        b"AA",
        b"AAAA",
        b"A" * 10,
        b"A" * 63,
        b"A" * 64,
        b"A" * 65,
        b"A" * 100,
        b"A" * 127,
        b"A" * 128,
        b"A" * 129,
        b"A" * 200,
        b"A" * 255,
        b"A" * 256,
        b"A" * 257,
        b"A" * 512,
        b"A" * 1000,
        b"A" * 10000,
        b"A" * 50000,
    ])
    def test_repeated_bytes_roundtrip(self, data):
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data, (
            f"Length mismatch: original={len(data)} decompressed={len(decompressed)}"
        )

    @pytest.mark.parametrize("data", [
        b"\x00" * 100,
        b"\x00" * 1000,
        b"\xff" * 100,
        b"\xff" * 1000,
    ])
    def test_extreme_bytes_roundtrip(self, data):
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    @pytest.mark.parametrize("data", [
        bytes(range(256)),
        bytes(range(256)) * 2,
        bytes(range(256)) * 4,
        bytes(range(128)) * 8,
    ])
    def test_counter_patterns_roundtrip(self, data):
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    @pytest.mark.parametrize("data", [
        b"Hello, World!",
        b"Hello, World! Hello, World!",
        b"Hello, World!" * 20,
        b"The quick brown fox jumps over the lazy dog" * 5,
        b"abcdefghij" * 100,
    ])
    def test_text_patterns_roundtrip(self, data):
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_random_data_roundtrip(self):
        import random
        random.seed(42)
        data = bytes(random.randint(0, 255) for _ in range(5000))
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    @pytest.mark.parametrize("window_sz2", [4, 5, 6, 7, 8, 9, 10, 12, 14])
    def test_different_window_sizes_roundtrip(self, window_sz2):
        data = b"ABCDEF" * 100
        lookahead_sz2 = window_sz2 - 1
        compressed = compress(data, window_sz2, lookahead_sz2)
        decompressed = decompress(compressed, window_sz2, lookahead_sz2)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 3. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test specific edge cases and boundary conditions."""

    def test_empty_input(self):
        """Empty input should produce empty output."""
        compressed = compress(b"", 8, 7)
        assert compressed == b""
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == b""

    def test_single_byte(self):
        """Single byte input."""
        for val in range(256):
            data = bytes([val])
            compressed = compress(data, 8, 7)
            decompressed = decompress(compressed, 8, 7)
            assert decompressed == data

    def test_window_boundary(self):
        """Inputs exactly at window size boundaries."""
        for ws2 in [4, 5, 6, 7, 8]:
            ws = 1 << ws2
            # Exactly window size
            data = b"A" * ws
            compressed = compress(data, ws2, ws2 - 1)
            decompressed = decompress(compressed, ws2, ws2 - 1)
            assert decompressed == data
            # Just over window size
            data = b"A" * (ws + 1)
            compressed = compress(data, ws2, ws2 - 1)
            decompressed = decompress(compressed, ws2, ws2 - 1)
            assert decompressed == data

    def test_lookahead_boundary(self):
        """Inputs at lookahead size boundaries."""
        for la2 in [3, 4, 5, 6]:
            la = 1 << la2
            data = b"A" * (la + 50)
            ws2 = la2 + 2
            compressed = compress(data, ws2, la2)
            decompressed = decompress(compressed, ws2, la2)
            assert decompressed == data

    def test_large_input(self):
        """Very large input (1 MB)."""
        data = b"X" * (1024 * 1024)
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data
        # Should be heavily compressed
        assert len(compressed) < len(data) * 0.1

    def test_alternating_pattern(self):
        """Alternating byte pattern."""
        data = bytes([i % 256 for i in range(10000)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_block_repeats(self):
        """Repeating blocks of varying sizes."""
        for block_size in [1, 2, 4, 8, 16, 32, 64, 128, 255, 256, 257]:
            block = bytes(range(block_size)) if block_size <= 256 else b"\xAA" * block_size
            data = block * 10
            compressed = compress(data, 8, 7)
            decompressed = decompress(compressed, 8, 7)
            assert decompressed == data, f"Failed for block_size={block_size}"


# ---------------------------------------------------------------------------
# 4. Encoder state machine tests
# ---------------------------------------------------------------------------

class TestEncoderStateMachine:
    """Test encoder internal state machine behavior."""

    def test_finish_before_empty(self):
        """Calling finish() before all data is processed."""
        data = b"Hello"
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(data)
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        assert len(out) > 0
        # Verify the encoded data decompresses correctly
        from heatshrink_decoder import HeatshrinkDecoder
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(bytes(out))
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data

    def test_invalid_window_size(self):
        """Invalid window sizes should raise ValueError."""
        with pytest.raises(ValueError):
            HeatshrinkEncoder(3, 2)  # too small
        with pytest.raises(ValueError):
            HeatshrinkEncoder(16, 8)  # too large

    def test_invalid_lookahead_size(self):
        """Invalid lookahead sizes should raise ValueError."""
        with pytest.raises(ValueError):
            HeatshrinkEncoder(8, 2)  # too small
        with pytest.raises(ValueError):
            HeatshrinkEncoder(8, 8)  # must be < window_sz2


# ---------------------------------------------------------------------------
# 5. Decoder state machine tests
# ---------------------------------------------------------------------------

class TestDecoderStateMachine:
    """Test decoder internal state machine behavior."""

    def test_decoder_with_larger_buffer(self):
        """Decoder should work correctly with various buffer sizes."""
        data = b"ABCDEFGHIJ" * 100
        compressed = compress(data, 8, 7)

        # Test with different input buffer sizes
        for ibs in [32, 64, 128, 256]:
            dec = HeatshrinkDecoder(8, 7, input_buffer_size=ibs)
            dec.sink(compressed)
            dec.finish()
            result = bytearray()
            while dec.finish():
                dec.poll(result)
            assert bytes(result) == data, f"Failed with input_buffer_size={ibs}"


# ---------------------------------------------------------------------------
# 6. Compression ratio sanity checks
# ---------------------------------------------------------------------------

class TestCompressionRatios:
    """Basic sanity checks on compression ratios."""

    def test_repeated_data_compresses(self):
        """Highly repetitive data should compress significantly."""
        data = b"A" * 10000
        compressed = compress(data, 8, 7)
        ratio = len(compressed) / len(data)
        assert ratio < 0.1, f"Repetitive data not compressed enough: {ratio:.3f}"

    def test_random_data_compresses_less(self):
        """Random data should not compress as much as repetitive data."""
        import random
        random.seed(123)
        data = bytes(random.randint(0, 255) for _ in range(5000))
        compressed = compress(data, 8, 7)
        ratio = len(compressed) / len(data)
        # Random data compresses to roughly the same size (heatshrink overhead)
        assert ratio < 1.5, f"Random data not compressing: ratio={ratio:.3f}"

    def test_compressed_is_never_larger_than_original_by_more_than_2x(self):
        """Compressed data should not be absurdly larger than original."""
        import random
        random.seed(999)
        for _ in range(10):
            size = random.randint(1, 10000)
            data = bytes(random.randint(0, 255) for _ in range(size))
            compressed = compress(data, 8, 7)
            assert len(compressed) < len(data) * 2, (
                f"Compressed ({len(compressed)}) too large vs original ({len(data)})"
            )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
