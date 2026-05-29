#!/usr/bin/env python3
"""
Additional tests for Heatshrink C vs Python behavioral differences.
Focuses on edge cases, API differences, and subtle behavioral discrepancies.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import heatshrink_encoder as enc_mod
import heatshrink_decoder as dec_mod
from heatshrink_encoder import compress, HeatshrinkEncoder
from heatshrink_decoder import decompress, HeatshrinkDecoder

# Try to import C reference for cross-validation
try:
    import subprocess
    C_AVAILABLE = os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink'))
except Exception:
    C_AVAILABLE = False


def compress_with_params(data, window_sz2, lookahead_sz2):
    """Compress with specific parameters using Python encoder."""
    enc = HeatshrinkEncoder(window_sz2, lookahead_sz2)
    result = bytearray()
    offset = 0
    while offset < len(data):
        cp_sz = enc.sink(data[offset:])
        offset += cp_sz
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
    enc.finish()
    while True:
        out, more = enc.poll()
        result.extend(out)
        if not more:
            break
    return bytes(result)


def decode_with_params(compressed, window_sz2, lookahead_sz2, input_buf_size=None):
    """Decode with specific parameters using Python decoder."""
    if input_buf_size is None:
        input_buf_size = max(32, len(compressed) + 32)
    dec = HeatshrinkDecoder(window_sz2, lookahead_sz2, input_buffer_size=input_buf_size)
    result = bytearray()
    dec.sink(compressed)
    dec.finish()
    while dec.finish():
        dec.poll(result)
    return bytes(result)


def roundtrip(data, window_sz2, lookahead_sz2):
    """Compress and decompress, return result."""
    compressed = compress_with_params(data, window_sz2, lookahead_sz2)
    return decode_with_params(compressed, window_sz2, lookahead_sz2, len(compressed) + 32)


# =============================================================================
# Minimal window/lookahead tests (window_sz2=4, lookahead_sz2=3)
# =============================================================================

class TestMinimalWindowLookahead:
    """Test with smallest allowed window_sz2=4, lookahead_sz2=3."""

    def test_single_byte(self):
        assert roundtrip(b'\x00', 4, 3) == b'\x00'
        assert roundtrip(b'\xff', 4, 3) == b'\xff'
        assert roundtrip(b'\x42', 4, 3) == b'\x42'

    def test_two_bytes_no_match(self):
        data = b'\x00\x01'
        assert roundtrip(data, 4, 3) == data

    def test_two_same_bytes(self):
        # With window=16, lookahead=8, "aa" should be: literal 'a' + backref(1, 1)
        data = b'aa'
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_three_same_bytes(self):
        data = b'aaa'
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_four_same_bytes(self):
        data = b'aaaa'
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_eight_same_bytes(self):
        data = b'a' * 8
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_repeating_pattern_abc(self):
        data = b'abcabcabc'
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_repeating_pattern_ab(self):
        data = b'abababab'
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_all_0xff(self):
        data = b'\xff' * 16
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_incrementing_bytes(self):
        data = bytes(range(16))
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_decrementing_bytes(self):
        data = bytes(range(15, -1, -1))
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_window_boundary_16_bytes(self):
        # Window size is 2^4 = 16 bytes
        # Data exactly at window boundary
        data = b'a' * 16
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_just_over_window_17_bytes(self):
        data = b'a' * 17
        result = roundtrip(data, 4, 3)
        assert result == data

    def test_20_bytes_with_pattern(self):
        data = b'abcdabcdabcdabcdabcd'
        result = roundtrip(data, 4, 3)
        assert result == data


# =============================================================================
# Encoder finish() behavior tests
# =============================================================================

class TestEncoderFinishBehavior:
    """Test encoder finish() edge cases."""

    def test_finish_with_no_data(self):
        """finish() called without any data - produces no output (matches C)."""
        enc = HeatshrinkEncoder(8, 7)
        enc.finish()
        output, more = enc.poll()
        # Empty input -> no output (matches C reference behavior)
        assert len(output) == 0
        # finish() should return DONE
        assert enc.finish() == 0  # FINISH_DONE

    def test_finish_called_twice(self):
        """Calling finish() twice should be safe."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'hello')
        assert enc.finish() == 1  # FINISH_MORE
        assert enc.finish() == 1  # Still MORE
        # Drain output
        while True:
            out, more = enc.poll()
            if not more:
                break
        assert enc.finish() == 0  # Now DONE

    def test_sink_after_finish_raises(self):
        """Sink after finish() should raise error."""
        enc = HeatshrinkEncoder(8, 7)
        enc.finish()
        with pytest.raises(RuntimeError):
            enc.sink(b'test')

    def test_finish_when_already_done(self):
        """finish() when encoding is complete should return DONE."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'hi')
        enc.finish()
        while True:
            out, more = enc.poll()
            if not more:
                break
        assert enc.finish() == 0
        assert enc.finish() == 0  # Multiple calls OK

    def test_finish_with_empty_input(self):
        """finish() with no data should produce no output (matches C)."""
        enc = HeatshrinkEncoder(8, 7)
        enc.finish()
        result = bytearray()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        # Empty input -> no output (matches C reference behavior)
        assert len(result) == 0

    def test_finish_state_transition_not_full_to_filled(self):
        """finish() should transition NOT_FULL -> FILLED state."""
        enc = HeatshrinkEncoder(8, 7)
        # Don't sink any data
        enc.finish()
        # State should have changed
        assert enc.state != enc_mod.HSES_NOT_FULL


# =============================================================================
# Decoder finish() behavior tests
# =============================================================================

class TestDecoderFinishBehavior:
    """Test decoder finish() edge cases."""

    def test_finish_with_no_input(self):
        """finish() with no data should return DONE."""
        dec = HeatshrinkDecoder(8, 7)
        assert dec.finish() == 0  # FINISH_DONE

    def test_finish_in_different_states(self):
        """finish() should return appropriate value in each state."""
        # After sinking some data but before consuming all
        compressed = compress_with_params(b'hello', 8, 7)
        
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        dec.sink(compressed)
        # Should have more to do
        assert dec.finish() == 1  # FINISH_MORE

    def test_finish_after_full_decode(self):
        """finish() after all data decoded should return DONE."""
        compressed = compress_with_params(b'hello', 8, 7)
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert dec.finish() == 0  # FINISH_DONE

    def test_finish_returns_0_or_1_not_boolean(self):
        """finish() should return 0 or 1, not True/False."""
        dec = HeatshrinkDecoder(8, 7)
        result = dec.finish()
        assert result in (0, 1)
        assert isinstance(result, int)

    def test_encoder_finish_returns_0_or_1(self):
        """Encoder finish() should return 0 or 1."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'test')
        result = enc.finish()
        assert result in (0, 1)
        assert isinstance(result, int)


# =============================================================================
# Output buffer behavior tests
# =============================================================================

class TestOutputBufferBehavior:
    """Test output buffer handling differences from C."""

    def test_poll_appends_to_buffer(self):
        """poll() should append to provided buffer."""
        compressed = compress_with_params(b'hello', 8, 7)
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        dec.sink(compressed)
        dec.finish()
        
        buf1 = bytearray()
        dec.poll(buf1)
        size_after_first = len(buf1)
        
        buf2 = bytearray()
        dec.poll(buf2)
        # Second poll should work on its own buffer
        # (decoder may have more output)

    def test_poll_without_buffer(self):
        """poll() without buffer should return bytes."""
        compressed = compress_with_params(b'hello', 8, 7)
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        dec.sink(compressed)
        dec.finish()
        
        result = dec.poll()
        assert isinstance(result, bytes)

    def test_encoder_poll_appends_to_buffer(self):
        """Encoder poll() should append to provided buffer."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'hello')
        enc.finish()
        
        buf = bytearray()
        enc.poll(buf)
        assert isinstance(buf, bytearray)
        assert len(buf) > 0

    def test_encoder_poll_returns_tuple(self):
        """Encoder poll() should return (bytes, more) tuple."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'hello')
        enc.finish()
        
        result = enc.poll()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bytes)
        assert result[1] in (0, 1)


# =============================================================================
# Back-reference edge cases
# =============================================================================

class TestBackrefEdgeCases:
    """Test back-reference specific edge cases."""

    def test_self_overlapping_backref(self):
        """Back-reference that overlaps with output position."""
        # "aaaaa" uses self-overlapping backref
        data = b'aaaaa'
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_large_backref(self):
        """Back-reference with length near lookahead max."""
        # lookahead_sz2=7 -> max backref length = 2^7 = 128
        data = b'a' * 128
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_backref_at_window_boundary(self):
        """Back-reference at exactly window size distance."""
        # window_sz2=8 -> window = 256
        data = b'a' * 256
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_backref_just_over_window(self):
        """Back-reference just over window size - should not match."""
        # With window=256, position 257 is outside window
        # "a" * 257 -> first 256 'a's can match, 257th cannot
        data = b'a' * 257
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_backref_just_under_window(self):
        """Back-reference just under window size."""
        data = b'a' * 255
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_only_backrefs_no_literals(self):
        """Data that encodes as mostly back-references."""
        data = b'abcabcabcabcabcabc'
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_backref_length_one(self):
        """Back-reference with length 1."""
        # Minimal backref: tag=0, index=N, count=1
        # This happens when a single byte matches
        data = b'abca'
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_many_short_backrefs(self):
        """Pattern that produces many short back-references."""
        data = b'abababababababab'
        result = roundtrip(data, 8, 7)
        assert result == data


# =============================================================================
# Input buffer size edge cases
# =============================================================================

class TestInputBufferSize:
    """Test decoder input buffer size edge cases."""

    def test_minimum_input_buffer(self):
        """Decoder with minimum input buffer size."""
        compressed = compress_with_params(b'hello world', 8, 7)
        # input_buffer_size = len(compressed) (minimum to fit)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=len(compressed))
        result = bytearray()
        dec.sink(compressed)
        dec.finish()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == b'hello world'

    def test_input_buffer_exactly_compressed_size(self):
        """Input buffer exactly matches compressed size."""
        compressed = compress_with_params(b'test data here', 8, 7)
        dec = HeatshrinkDecoder(8, 7, len(compressed))
        result = bytearray()
        dec.sink(compressed)
        dec.finish()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == b'test data here'

    def test_sink_partial_with_full_buffer(self):
        """Sink partial data when buffer fills up."""
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=5)
        # Sink 5 bytes (fills buffer)
        assert dec.sink(b'12345') == 5
        # Next sink should return 0 (buffer full)
        assert dec.sink(b'67890') == 0

    def test_sink_wraparound(self):
        """Test that circular buffer wraparound works correctly."""
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=10)
        # Sink 5 bytes
        assert dec.sink(b'12345') == 5
        # Sink 5 more (fills buffer)
        assert dec.sink(b'67890') == 5
        # Buffer is full


# =============================================================================
# State machine tests
# =============================================================================

class TestStateMachine:
    """Test encoder/decoder state machine transitions."""

    def test_encoder_initial_state(self):
        enc = HeatshrinkEncoder(8, 7)
        assert enc.state == enc_mod.HSES_NOT_FULL

    def test_encoder_state_after_sink(self):
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'hello')
        # Not full yet (need 256 bytes for window_sz2=8)
        assert enc.state == enc_mod.HSES_NOT_FULL

    def test_encoder_state_after_sink_full(self):
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'a' * 256)
        assert enc.state == enc_mod.HSES_FILLED

    def test_decoder_initial_state(self):
        dec = HeatshrinkDecoder(8, 7)
        assert dec.state == dec_mod.HSDS_TAG_BIT

    def test_encoder_states_are_integers(self):
        """All state constants should be integers."""
        states = [
            enc_mod.HSES_NOT_FULL, enc_mod.HSES_FILLED, enc_mod.HSES_SEARCH,
            enc_mod.HSES_YIELD_TAG_BIT, enc_mod.HSES_YIELD_LITERAL,
            enc_mod.HSES_YIELD_BR_INDEX, enc_mod.HSES_YIELD_BR_LENGTH,
            enc_mod.HSES_SAVE_BACKLOG, enc_mod.HSES_FLUSH_BITS, enc_mod.HSES_DONE
        ]
        for s in states:
            assert isinstance(s, int)

    def test_decoder_states_are_integers(self):
        states = [
            dec_mod.HSDS_TAG_BIT, dec_mod.HSDS_YIELD_LITERAL,
            dec_mod.HSDS_BACKREF_INDEX_MSB, dec_mod.HSDS_BACKREF_INDEX_LSB,
            dec_mod.HSDS_BACKREF_COUNT_MSB, dec_mod.HSDS_BACKREF_COUNT_LSB,
            dec_mod.HSDS_YIELD_BACKREF
        ]
        for s in states:
            assert isinstance(s, int)


# =============================================================================
# Reset behavior tests
# =============================================================================

class TestResetBehavior:
    """Test encoder/decoder reset behavior."""

    def test_decoder_reset(self):
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(b'test')
        dec.reset()
        assert dec.state == dec_mod.HSDS_TAG_BIT
        assert dec.input_size == 0

    def test_encoder_can_be_reused_via_constructor(self):
        """Encoder doesn't have reset(), use constructor for fresh instance."""
        enc1 = HeatshrinkEncoder(8, 7)
        enc1.sink(b'hello')
        # Create new encoder instead of reset
        enc2 = HeatshrinkEncoder(8, 7)
        assert enc2.state == enc_mod.HSES_NOT_FULL


# =============================================================================
# API misuse tests
# =============================================================================

class TestAPIMisuse:
    """Test error handling for API misuse."""

    def test_sink_while_encoding_raises(self):
        """Sink while encoding in progress should raise."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b'a' * 256)  # Fills buffer, triggers encoding
        # Now state is not NOT_FULL, sink should raise
        with pytest.raises(RuntimeError):
            enc.sink(b'more')

    def test_sink_after_finish_raises(self):
        with pytest.raises(RuntimeError):
            enc = HeatshrinkEncoder(8, 7)
            enc.finish()
            enc.sink(b'test')

    def test_invalid_window_sz2_too_small(self):
        with pytest.raises(ValueError):
            HeatshrinkEncoder(3, 3)

    def test_invalid_window_sz2_too_large(self):
        with pytest.raises(ValueError):
            HeatshrinkEncoder(16, 8)

    def test_invalid_lookahead_too_small(self):
        with pytest.raises(ValueError):
            HeatshrinkEncoder(8, 2)

    def test_invalid_lookahead_equal_to_window(self):
        with pytest.raises(ValueError):
            HeatshrinkEncoder(8, 8)

    def test_invalid_lookahead_greater_than_window(self):
        with pytest.raises(ValueError):
            HeatshrinkEncoder(8, 9)


# =============================================================================
# Cross-validation with C on specific patterns
# =============================================================================

class TestCReferenceComparison:
    """Compare Python output with C reference on specific patterns."""

    @pytest.mark.skipif(not C_AVAILABLE, reason="C reference not available")
    def test_c_identical_output_foo(self):
        """'foo' should produce identical output."""
        data = b'foo'
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(not C_AVAILABLE, reason="C reference not available")
    def test_c_identical_output_aaaaa(self):
        """'aaaaa' should produce identical output."""
        data = b'aaaaa'
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(not C_AVAILABLE, reason="C reference not available")
    def test_c_identical_output_abcdabcd(self):
        data = b'abcdabcd'
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(not C_AVAILABLE, reason="C reference not available")
    def test_c_identical_output_256_a(self):
        data = b'a' * 256
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(not C_AVAILABLE, reason="C reference not available")
    def test_c_identical_output_random_100(self):
        import random
        random.seed(42)
        data = bytes(random.randint(0, 255) for _ in range(100))
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @staticmethod
    def _compress_with_c(data, window_sz2, lookahead_sz2):
        try:
            result = subprocess.run(
                ['./heatshrink', '-w', str(window_sz2), '-l', str(lookahead_sz2)],
                input=data,
                capture_output=True,
                timeout=10,
                cwd=os.path.dirname(__file__)
            )
            return result.stdout
        except Exception:
            return None


# =============================================================================
# Break-even point tests
# =============================================================================

class TestBreakEvenPoint:
    """Test data around the break-even compression point."""

    def test_break_even_point_calculation(self):
        """Verify break-even point: 1 + window_sz2 + lookahead_sz2 = 16 bits for 8,7."""
        # break_even = (1 + 8 + 7) / 8 = 2 bytes
        # Match must be > 2 bytes to be worth encoding as backref
        enc = HeatshrinkEncoder(8, 7)
        # "abcde" - no matches, should be all literals
        enc.sink(b'abcde')
        enc.finish()
        result = bytearray()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        # 5 literals = 5 * 9 bits = 45 bits = 6 bytes
        # (1 tag bit + 8 data bits) * 5 = 45 bits -> 6 bytes
        assert len(result) == 6

    def test_3_byte_match_is_worth_it(self):
        """3-byte match should be encoded as backref (3 > 16/8=2)."""
        data = b'abcdefabc'  # 'abc' repeated, match length 3
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_2_byte_match_may_not_be_worth_it(self):
        """2-byte match: 2 <= 16/8=2, so may be encoded as literals."""
        data = b'abab'  # 'ab' repeated, match length 2
        result = roundtrip(data, 8, 7)
        assert result == data  # Should still decode correctly

    def test_1_byte_match_always_literal(self):
        """1-byte match: 1 <= 2, always encoded as literal."""
        data = b'aba'
        result = roundtrip(data, 8, 7)
        assert result == data


# =============================================================================
# Streaming encode/decode tests
# =============================================================================

class TestStreamingBehavior:
    """Test streaming encode/decode patterns."""

    def test_byte_by_byte_encode(self):
        """Encode one byte at a time."""
        data = b'hello world'
        enc = HeatshrinkEncoder(8, 7)
        result = bytearray()
        
        for byte in data:
            enc.sink(bytes([byte]))
            while True:
                out, more = enc.poll()
                result.extend(out)
                if not more:
                    break
        
        enc.finish()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        
        compressed = bytes(result)
        decompressed = decode_with_params(compressed, 8, 7, len(compressed) + 32)
        assert decompressed == data

    def test_byte_by_byte_decode(self):
        """Decode one compressed byte at a time, poll after each."""
        data = b'hello world'
        compressed = compress_with_params(data, 8, 7)
        
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        result = bytearray()
        
        for byte in compressed:
            dec.sink(bytes([byte]))
            # Poll after each byte to get any available output
            while True:
                chunk = dec.poll()
                if len(chunk) == 0:
                    break
                result.extend(chunk)
        
        # Mark input as finished
        dec.finish()
        while True:
            chunk = dec.poll()
            if len(chunk) == 0:
                break
            result.extend(chunk)
        
        assert bytes(result) == data

    def test_chunked_encode_decode(self):
        """Encode/decode in small chunks."""
        data = b'the quick brown fox jumps over the lazy dog'
        
        # Encode in chunks of 5 bytes
        enc = HeatshrinkEncoder(8, 7)
        compressed = bytearray()
        for i in range(0, len(data), 5):
            chunk = data[i:i+5]
            enc.sink(chunk)
            while True:
                out, more = enc.poll()
                compressed.extend(out)
                if not more:
                    break
        
        enc.finish()
        while True:
            out, more = enc.poll()
            compressed.extend(out)
            if not more:
                break
        
        # Decode in chunks of 3 bytes
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        result = bytearray()
        for i in range(0, len(compressed), 3):
            chunk = compressed[i:i+3]
            dec.sink(bytes(chunk))
            # Poll for available output
            while True:
                chunk_out = dec.poll()
                if len(chunk_out) == 0:
                    break
                result.extend(chunk_out)
        
        # Mark input as finished
        dec.finish()
        while True:
            chunk_out = dec.poll()
            if len(chunk_out) == 0:
                break
            result.extend(chunk_out)
        
        assert bytes(result) == data


# =============================================================================
# Large data tests
# =============================================================================

class TestLargeData:
    """Test with larger inputs."""

    def test_1k_repeating_pattern(self):
        data = (b'abcdefgh' * 128)  # 1024 bytes
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_1k_random(self):
        import random
        random.seed(12345)
        data = bytes(random.randint(0, 255) for _ in range(1024))
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_4k_repeating(self):
        data = (b'xyz' * (4096 // 3 + 1))[:4096]
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_8k_all_same(self):
        data = b'\x55' * 8192
        result = roundtrip(data, 8, 7)
        assert result == data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
