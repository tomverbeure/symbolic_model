#ifndef DOWNSCALER_H
#define DOWNSCALER_H

#include "ap_axi_sdata.h"
#include "hls_stream.h"

#define INPUT_WIDTH             64
#define INPUT_HEIGHT            64
#define INPUT_SB_SIZE           16
#define PIXELS_PER_TILE         16

#define OUTPUT_WIDTH            INPUT_WIDTH/2
#define OUTPUT_HEIGHT           INPUT_HEIGHT/2

#define PIXEL_WIDTH             10

typedef ap_axis<PIXEL_WIDTH * 16, 0, 0, 0>  t_tile;
typedef ap_uint<PIXEL_WIDTH>                t_pxl;

void downscaler(hls::stream<t_tile> &tile_in_chn, hls::stream<t_tile> &tile_out_chn);


#endif
