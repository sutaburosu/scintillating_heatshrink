// "batman2" (GIF orig:144 raw_payload:280 shrunk_payload:95 total:103 bytes)
// Compared to GIF: 71.53% 	Compared to raw: 36.79%
// using GIF index 11 as our transparency index 0 (blackened)
// ./heatshrink -w 8 -l 7 (background = 0; transparency = 11; )

FL_PROGMEM const struct HSpr_batman2 {
	uint16_t datasize = 95;
	uint16_t frames = 1;
	uint16_t duration = 0;
	uint8_t flags = 0;
	uint8_t palette_entries = 8;
	uint8_t crgb[0] = {
		// 0x00, 0x00, 0x00,  // original palette index 11
		// 0x00, 0x00, 0x00,  // original palette index 10
		// 0xff, 0xff, 0xff,  // original palette index 0
		// 0x99, 0x99, 0x99,  // original palette index 3
		// 0x99, 0x66, 0x33,  // original palette index 4
		// 0xff, 0xcc, 0x99,  // original palette index 1
		// 0xcc, 0x99, 0x66,  // original palette index 2
		// 0x66, 0x33, 0x00,  // original palette index 5
	};
	uint8_t hs_data[95] = {
		0x00, 0x05, 0xff, 0xff, 0xff, 0xf9, 0x90, 0x00, 0x2b, 0x34, 0xcf, 0xff, 0xcc, 0xcc, 0xf3, 0x33, 
		0x36, 0x6b, 0x34, 0xcc, 0x2c, 0x16, 0x02, 0x03, 0x0c, 0x00, 0x0e, 0x0f, 0x08, 0x10, 0x15, 0x01, 
		0x00, 0x04, 0x07, 0x8f, 0x08, 0x09, 0x07, 0xa2, 0x81, 0x40, 0x60, 0x30, 0x30, 0x78, 0xa8, 0x20, 
		0x7c, 0x1c, 0x10, 0x1e, 0x2a, 0x0b, 0x05, 0x83, 0x41, 0x60, 0xe0, 0xf1, 0x50, 0x68, 0x3c, 0x1e, 
		0x08, 0x0f, 0x17, 0x05, 0x83, 0x41, 0xa0, 0xa2, 0xf1, 0x80, 0xf0, 0x50, 0x62, 0xf0, 0x91, 0xf8, 
		0x22, 0x08, 0x23, 0xe8, 0xc4, 0x00, 0x60, 0x68, 0x90, 0x80, 0x40, 0x70, 0xc0, 0x00, 0x20, 
	};
} HSpr_batman2;
