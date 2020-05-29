// "unionflag16" (GIF orig:123 raw_payload:277 shrunk_payload:92 total:100 bytes)
// Compared to GIF: 81.30% 	Compared to raw: 36.10%
// ./heatshrink -w 8 -l 7 (background = 0; )

FL_PROGMEM const struct HSpr_unionflag16 {
	uint16_t datasize = 92;
	uint16_t frames = 1;
	uint16_t duration = 1000;
	uint8_t flags = 0;
	uint8_t palette_entries = 7;
	uint8_t crgb[0] = {
		// 0x00, 0x00, 0x00,  // original palette index 0
		// 0x00, 0x00, 0x00,  // original palette index 1
		// 0x7f, 0x7f, 0xcd,  // original palette index 5
		// 0x00, 0x00, 0x9b,  // original palette index 3
		// 0xff, 0x00, 0x00,  // original palette index 2
		// 0xc7, 0xc7, 0xea,  // original palette index 6
		// 0xff, 0x50, 0x50,  // original palette index 4
	};
	uint8_t hs_data[92] = {
		0x00, 0x05, 0xbf, 0xdf, 0xf9, 0xb0, 0x08, 0x06, 0x6f, 0xff, 0x00, 0x80, 0x71, 0xf8, 0xfe, 0xaf, 
		0xfd, 0x42, 0xa1, 0x01, 0x00, 0x1e, 0x1f, 0x90, 0x81, 0x40, 0xc0, 0x00, 0xa0, 0x10, 0x48, 0x24, 
		0x00, 0x0e, 0x0e, 0x0b, 0x06, 0x83, 0x41, 0x02, 0x20, 0xc1, 0xe1, 0x60, 0xa0, 0xc0, 0x40, 0x40, 
		0x90, 0x20, 0x78, 0x30, 0x40, 0x48, 0x18, 0xd4, 0x30, 0x3c, 0x10, 0x20, 0x38, 0x00, 0xe8, 0xbc, 
		0x7c, 0x0c, 0x96, 0x0a, 0x0d, 0x05, 0x07, 0x83, 0x04, 0x04, 0x34, 0x82, 0x02, 0x02, 0x37, 0x86, 
		0x08, 0x83, 0x06, 0x83, 0x47, 0x89, 0x81, 0x2b, 0x88, 0x37, 0xcf, 0x80, 
	};
} HSpr_unionflag16;
