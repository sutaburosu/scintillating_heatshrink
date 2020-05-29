#ifndef HSPRITES_HH
#define HSPRITES_HH 1
#include "gif2h.h"

#include "GIF/35disk.h"                            //  156 bytes  12 cols   1 frame  Compared to GIF:  92.31%
#include "GIF/load.h"                              //  939 bytes  27 cols   8 frames Compared to GIF:  85.68%
#include "GIF/vn.h"                                //   65 bytes   4 cols   2 frames Compared to GIF:  35.33%
#include "GIF/unionflag16.h"                       //  100 bytes   7 cols   1 frame  Compared to GIF:  81.30%
#include "GIF/eu.h"                                //   83 bytes   5 cols   1 frame  Compared to GIF:  57.24%
#include "GIF/ghost.h"                             //  146 bytes   7 cols   1 frame  Compared to GIF:  86.90%
#include "GIF/scheisse.h"                          //  312 bytes  34 cols   4 frames Compared to GIF:  65.27%
#include "GIF/devil_nod.h"                         //  843 bytes  51 cols   4 frames Compared to GIF: 102.06%
#include "GIF/kputrummis.h"                        //  396 bytes  29 cols   2 frames Compared to GIF:  85.71%
#include "GIF/rjb.h"                               //  892 bytes  31 cols  14 frames Compared to GIF:  95.50%
#include "GIF/owl.h"                               //  333 bytes   6 cols  20 frames Compared to GIF:  20.86%
#include "GIF/twylogo.h"                           //  751 bytes   9 cols  59 frames Compared to GIF:  18.89%
#include "GIF/gear.h"                              //  731 bytes  18 cols   8 frames Compared to GIF:  79.98%
#include "GIF/16x16_oric.h"                        // 3061 bytes  32 cols  26 frames Compared to GIF:  77.55%
#include "GIF/zx_k_ref.h"                          //   64 bytes   3 cols   2 frames Compared to GIF:  34.41%
#include "GIF/invader.h"                           //  231 bytes   4 cols   6 frames Compared to GIF:  57.75%
#include "GIF/c64.h"                               //   88 bytes   6 cols   1 frame  Compared to GIF:  14.92%
#include "GIF/amigaroll_trs.h"                     //  844 bytes  17 cols   8 frames Compared to GIF:  47.85%
#include "GIF/joystick.h"                          //  543 bytes  44 cols   6 frames Compared to GIF:  50.65%
#include "GIF/slime.h"                             //  220 bytes   5 cols   4 frames Compared to GIF:   3.26%
#include "GIF/DigDug16x16.h"                       //  121 bytes   5 cols   2 frames Compared to GIF:   2.42%
#include "GIF/octorokblue.h"                       //  374 bytes   6 cols   3 frames Compared to GIF:  98.42%
#include "GIF/ptititi.h"                           //  164 bytes   9 cols   1 frame  Compared to GIF:  94.80%
#include "GIF/burgertime.h"                        // 1203 bytes   6 cols  26 frames Compared to GIF:  58.63%
#include "GIF/pouet_avatar_poi_charly_walk2.h"     //  772 bytes   9 cols   8 frames Compared to GIF:  80.08%
#include "GIF/rockhell.h"                          //  408 bytes   7 cols   4 frames Compared to GIF:  79.22%
#include "GIF/pouet_avatar_mario.h"                //  245 bytes  14 cols   2 frames Compared to GIF:  74.70%
#include "GIF/kirby_run.h"                         //  545 bytes  11 cols   4 frames Compared to GIF:  95.11%
#include "GIF/bub.h"                               //  240 bytes   7 cols   4 frames Compared to GIF:  77.67%
#include "GIF/sirlord.h"                           //  222 bytes   4 cols   4 frames Compared to GIF:  70.93%
#include "GIF/plane.h"                             //  151 bytes  10 cols   3 frames Compared to GIF:  41.94%
#include "GIF/fire.h"                              //  701 bytes   8 cols   8 frames Compared to GIF:  62.20%
#include "GIF/bird16.h"                            //  188 bytes   4 cols   3 frames Compared to GIF:  80.34%
#include "GIF/mspacman.h"                          //  203 bytes   5 cols   4 frames Compared to GIF:  66.34%
#include "GIF/ghost3.h"                            //  185 bytes   6 cols   2 frames Compared to GIF:  29.84%
#include "GIF/batman2.h"                           //  103 bytes   8 cols   1 frame  Compared to GIF:  71.53%
#include "GIF/lemming.h"                           //  167 bytes   9 cols   1 frame  Compared to GIF:  98.82%
#include "GIF/mwk.h"                               //  261 bytes   4 cols   5 frames Compared to GIF:  56.49%
#include "GIF/gwain2.h"                            // 1441 bytes  16 cols  10 frames Compared to GIF: 101.69%
#include "GIF/scoopexrulez.h"                      //  823 bytes  15 cols   4 frames Compared to GIF:  89.27%
#include "GIF/8bit_avatar.h"                       //  296 bytes  16 cols   5 frames Compared to GIF:  74.56%
#include "GIF/ganja16x16.h"                        //  235 bytes  12 cols   1 frame  Compared to GIF: 117.50%

FL_PROGMEM extern const HSprite *const hsprite_list[] = {
  (HSprite*) &HSpr_35disk,
  (HSprite*) &HSpr_load,
  (HSprite*) &HSpr_vn,
  (HSprite*) &HSpr_unionflag16,
  (HSprite*) &HSpr_eu,
  (HSprite*) &HSpr_ghost,
  (HSprite*) &HSpr_scheisse,
  (HSprite*) &HSpr_devil_nod,
  (HSprite*) &HSpr_kputrummis,
  (HSprite*) &HSpr_rjb,
  (HSprite*) &HSpr_owl,
  (HSprite*) &HSpr_twylogo,
  (HSprite*) &HSpr_gear,
  (HSprite*) &HSpr_16x16_oric,
  (HSprite*) &HSpr_zx_k_ref,
  (HSprite*) &HSpr_invader,
  (HSprite*) &HSpr_c64,
  (HSprite*) &HSpr_amigaroll_trs,
  (HSprite*) &HSpr_joystick,
  (HSprite*) &HSpr_slime,
  (HSprite*) &HSpr_DigDug16x16,
  (HSprite*) &HSpr_octorokblue,
  (HSprite*) &HSpr_ptititi,
  (HSprite*) &HSpr_burgertime,
  (HSprite*) &HSpr_pouet_avatar_poi_charly_walk2,
  (HSprite*) &HSpr_rockhell,
  (HSprite*) &HSpr_pouet_avatar_mario,
  (HSprite*) &HSpr_kirby_run,
  (HSprite*) &HSpr_bub,
  (HSprite*) &HSpr_sirlord,
  (HSprite*) &HSpr_plane,
  (HSprite*) &HSpr_fire,
  (HSprite*) &HSpr_bird16,
  (HSprite*) &HSpr_mspacman,
  (HSprite*) &HSpr_ghost3,
  (HSprite*) &HSpr_batman2,
  (HSprite*) &HSpr_lemming,
  (HSprite*) &HSpr_mwk,
  (HSprite*) &HSpr_gwain2,
  (HSprite*) &HSpr_scoopexrulez,
  (HSprite*) &HSpr_8bit_avatar,
  (HSprite*) &HSpr_ganja16x16,
};
#define HSPRITES_N (sizeof(hsprite_list) / sizeof(hsprite_list[0]))
#endif
