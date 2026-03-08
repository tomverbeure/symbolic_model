#include <iostream>
#include <array>

#include "downscaler_impl.h"

void downscaler(hls::stream<t_tile> &tile_in_chn, hls::stream<t_tile> &tile_out_chn) 
{
    #pragma HLS INTERFACE axis port=tile_in_chn
    #pragma HLS INTERFACE axis port=tile_out_chn
    #pragma HLS INTERFACE ap_ctrl_none port=return

    static t_pxl    above_left_pixel;
    static t_pxl    above_pixels[INPUT_SB_SIZE / 2];
    static t_pxl    left_pixels[INPUT_SB_SIZE * 3 / 4];

    typedef std::array<t_pxl, 2> t_pxl2;
    typedef std::array<t_pxl, 4> t_pxl4;

    static hls::stream<t_pxl2>  dma_fifo;
    #pragma HLS STREAM variable=dma_fifo type=fifo depth=OUTPUT_WIDTH

    static hls::stream<t_pxl4>  output_merge_fifo;
    #pragma HLS STREAM variable=output_merge_fifo type=fifo depth=OUTPUT_WIDTH

    static t_pxl    tile_left_pixels[3];
    static t_pxl    tile_above_pixels[2];

    static t_pxl    input_tile[16];
    static t_pxl    output_tile[16];

    for(int sb_y = 0; sb_y < INPUT_HEIGHT / INPUT_SB_SIZE; ++ sb_y){
        for(int sb_x = 0; sb_x < INPUT_HEIGHT / INPUT_SB_SIZE; ++ sb_x){
            std::cout << "SB(" << sb_x << "," << sb_y <<  "):" << std::endl;

            if (sb_y != 0){
                for(int x = 0; x<INPUT_SB_SIZE/4; ++x){
                    t_pxl2 dma_duo = dma_fifo.read();

                    above_pixels[2 * x    ] = dma_duo[0];
                    above_pixels[2 * x + 1] = dma_duo[1];
                }
            }

            for(int tile_y = 0; tile_y < INPUT_SB_SIZE/4; ++tile_y){
                for(int tile_x = 0; tile_x < INPUT_SB_SIZE/4; ++tile_x){
                    t_tile tile_in;
                    std::cout << "Fetching input tile (" << tile_x << "," << tile_y <<  ")" << std::endl;
                    tile_in_chn.read(tile_in);

                    for(int i=0;i<16;++i){
                        #pragma HLS UNROLL
                        input_tile[i]    = tile_in.data.range(PIXEL_WIDTH * (i+1) -1, PIXEL_WIDTH * i);
                    }

                    bool is_bottom_row_sb   = sb_y == INPUT_HEIGHT/INPUT_SB_SIZE -1;
                    bool is_bottom_row_tile = tile_y == INPUT_SB_SIZE/4 -1;
                    bool is_right_col_tile  = tile_x == INPUT_SB_SIZE/4 -1;


                    if (sb_x == 0 && sb_y == 0 && tile_x == 0 && tile_y == 0){
                        above_left_pixel    = input_tile[0];
                    }

                    if (tile_x == 0){
                        if (sb_x == 0){
                            tile_left_pixels[0] = input_tile[0] + input_tile[4];
                            tile_left_pixels[1] = input_tile[4] + input_tile[8] + input_tile[12];
                            tile_left_pixels[2] = input_tile[12];
                        }
                        else{
                            tile_left_pixels[0] = left_pixels[tile_y * 3];
                            tile_left_pixels[1] = left_pixels[tile_y * 3 + 1];
                            tile_left_pixels[2] = left_pixels[tile_y * 3 + 2];
                        }
                    }

                    if (sb_y == 0 && tile_y == 0){
                        tile_above_pixels[0]    = above_left_pixel + input_tile[0] + input_tile[1];
                        tile_above_pixels[1]    = input_tile[1] + input_tile[2] + input_tile[3];
                    }
                    else{
                        tile_above_pixels[0]    = above_pixels[tile_x * 2];
                        tile_above_pixels[1]    = above_pixels[tile_x * 2 + 1];
                    }

                    t_pxl p00 =                        tile_above_pixels[0] +
                                 tile_left_pixels[0] + input_tile[0] +  input_tile[1] +
                                                       input_tile[4] +  input_tile[5] ;

                    t_pxl p10 =                        tile_above_pixels[1] +
                                      input_tile[ 1] + input_tile[ 2] + input_tile[ 3] +
                                      input_tile[ 5] + input_tile[ 6] + input_tile[ 7] ;

                    t_pxl p01 =  tile_left_pixels[1] + input_tile[ 4] + input_tile[ 5] +
                                                       input_tile[ 8] + input_tile[ 9] + 
                                                       input_tile[12] + input_tile[13] ; 

                    t_pxl p11 =       input_tile[ 5] + input_tile[ 6] + input_tile[ 7] +
                                      input_tile[ 9] + input_tile[10] + input_tile[11] +
                                      input_tile[13] + input_tile[14] + input_tile[15] ; 

                    if ( (tile_y & 1) == 0){
                        t_pxl4 quad_out;
                        quad_out[0] = p00;
                        quad_out[1] = p01;
                        quad_out[2] = p10;
                        quad_out[3] = p11;

                        output_merge_fifo.write(quad_out);
                    }
                    else{
                        t_pxl4 prev_p  = output_merge_fifo.read();

                        if ((tile_x & 1) == 0){
                            output_tile[0]  = prev_p[0];
                            output_tile[1]  = prev_p[1];
                            output_tile[4]  = prev_p[2];
                            output_tile[5]  = prev_p[3];

                            output_tile[8]  = p00;
                            output_tile[9]  = p10;
                            output_tile[12] = p01;
                            output_tile[13] = p11;
                        }
                        else{
                            output_tile[2]  = prev_p[0];
                            output_tile[3]  = prev_p[1];
                            output_tile[6]  = prev_p[2];
                            output_tile[7]  = prev_p[3];

                            output_tile[10]  = p00;
                            output_tile[11]  = p10;
                            output_tile[14]  = p01;
                            output_tile[15]  = p11;

                            t_tile tile_out;
                            for(int i=0;i<16;++i){
                                #pragma HLS UNROLL
                                tile_out.data.range(PIXEL_WIDTH * (i+1) -1, PIXEL_WIDTH * i) = output_tile[i];
                            }
                            tile_out_chn.write(tile_in);
                        }
                    }

                    t_pxl2  above_pixels_nxt;

                    above_pixels_nxt[0]     = tile_left_pixels[2] + input_tile[12] + input_tile[13];
                    above_pixels_nxt[1]     = input_tile[13]      + input_tile[14] + input_tile[15];

                    above_pixels[tile_x * 2]        = above_pixels_nxt[0];
                    above_pixels[tile_x * 2 + 1]    = above_pixels_nxt[1];

                    if (!is_bottom_row_sb && is_bottom_row_tile){
                        dma_fifo.write(above_pixels_nxt);
                    }

                    tile_left_pixels[0] = input_tile[3] + input_tile[ 7];
                    tile_left_pixels[1] = input_tile[7] + input_tile[11] + input_tile[15];
                    tile_left_pixels[2] = input_tile[15];

                    if (is_right_col_tile){
                        left_pixels[tile_y * 3]     = tile_left_pixels[0];
                        left_pixels[tile_y * 3 + 1] = tile_left_pixels[1];
                        left_pixels[tile_y * 3 + 2] = tile_left_pixels[2];
                    }

                    if (sb_y == 0 && tile_y == 0){
                        above_left_pixel    = input_tile[3];
                    }
                }
            }
        }
    }
}

