#ifndef FASTLED_ADDITIONS_HH
#define FASTLED_ADDITIONS_HH 1

// untested portability to non-AVR systems
#if FASTLED_USE_PROGMEM == 1
#define FL_PGM_READ_PTR_NEAR(x) (pgm_read_ptr_near(x))
#else
#define FL_PGM_READ_PTR_NEAR(addr) ({typeof(addr) _addr = (addr); *(void * const *)(_addr); })
#define memcpy_P(dest, src, n) memcpy(dest, src, n)
#endif

CRGB fadeTowardColour(CRGB& cur, const CRGB& target, uint8_t amount);
CRGB fadeTowardColour_video(CRGB& cur, const CRGB& target, uint8_t amount);
void nblendU8TowardU8(uint8_t& cur, const uint8_t target, uint8_t amount);
void nblendU8TowardU8_video(uint8_t& cur, const uint8_t target, uint8_t amount);
CRGB ColorFromPaletteExtended(const CRGBPalette16& pal, uint16_t index, uint8_t brightness, TBlendType blendType);
CRGB ColorFromPaletteExtended(const CRGBPalette32& pal, uint16_t index, uint8_t brightness, TBlendType blendType);

#endif