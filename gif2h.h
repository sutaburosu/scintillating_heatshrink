// structures to hold heatshrink recompressed animated GIFs

#ifndef __INC_GIF2H_H
#define __INC_GIF2H_H

#include <stdint.h>
#include <FastLED.h>

#ifndef GIF2H_MAX_PALETTE_ENTRIES
#define GIF2H_MAX_PALETTE_ENTRIES 16
#endif
#ifndef GIF2H_NUM_PIXELS
#define GIF2H_NUM_PIXELS 256
#endif

typedef struct HSprite {
    uint16_t datasize;
    uint16_t frames;
    uint16_t duration;
    uint8_t flags;
    uint8_t palette_entries;
    CRGB palette[];
    uint8_t hs_data[];
} HSprite;

typedef struct HStatus {
  uint32_t last_millis;
  heatshrink_decoder hsd;
  size_t heatsunk;
  uint16_t frame;
  uint8_t hs_spr_n = -1;
  uint8_t loops;
  CRGB palette[GIF2H_MAX_PALETTE_ENTRIES];
  uint8_t pixels[GIF2H_NUM_PIXELS];
} HStatus;

#endif