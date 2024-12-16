#! /usr/bin/env python3
from pprint import pprint

debug   = False

INPUT_WIDTH	            = 32
INPUT_HEIGHT	        = 32
INPUT_SUPER_BLOCK_SIZE  = 8

OUTPUT_WIDTH	        = INPUT_WIDTH//2
OUTPUT_HEIGHT	        = INPUT_HEIGHT//2
OUTPUT_SUPER_BLOCK_SIZE = INPUT_SUPER_BLOCK_SIZE//2

# key: 	(x,y) coordinates with x and y 0->63
# value: list with input pixel coordinates. The list is sorted
#        in left-to-right, then top-to-bottom scan order.
#        When an input pixel is used multiple times due to
#        picture boundary duplication, then it has multiple
#        entries.
ref_output_pixels	= {}

def reference_model():
    for y in range(OUTPUT_HEIGHT):
        for x in range(OUTPUT_WIDTH):
            ref_output_pixels[ (x,y) ] = []

            x_near_sb_boundary  = ( (x % OUTPUT_SUPER_BLOCK_SIZE) == 0) or ( (x % OUTPUT_SUPER_BLOCK_SIZE) == OUTPUT_SUPER_BLOCK_SIZE-1)
            y_near_sb_boundary  = ( (y % OUTPUT_SUPER_BLOCK_SIZE) == 0) or ( (y % OUTPUT_SUPER_BLOCK_SIZE) == OUTPUT_SUPER_BLOCK_SIZE-1)
            
            if x_near_sb_boundary or y_near_sb_boundary:
                filter_size = 3
            else:
                filter_size = 5

            for sy in range(2*y-filter_size//2,2*y+filter_size//2+1):

                if sy<0:
                    sy_final = 0
                elif sy >= INPUT_HEIGHT:
                    sy_final = INPUT_HEIGHT-1
                else:
                    sy_final = sy

                for sx in range(2*x-filter_size//2,2*x+filter_size//2+1):

                    if sx<0:
                        sx_final = 0
                    elif sx >= INPUT_WIDTH:
                        sx_final = INPUT_WIDTH-1
                    else:
                        sx_final = sx

                    ref_output_pixels[ (x,y) ].append( (sx_final,sy_final) )

            if debug:
                print(x, y, "=>", ref_output_pixels[ (x,y) ])

def gen_input_stream():
    # Generate stream with input pixels, super block by super block, then
    # in tiles of 4x4 pixels

    input_tiles     = []

    # Scan through all super blocks
    for sb_y in range(INPUT_HEIGHT//INPUT_SUPER_BLOCK_SIZE):
        for sb_x in range(INPUT_WIDTH//INPUT_SUPER_BLOCK_SIZE):

            # Scan through all tiles
            for tile_y in range(INPUT_SUPER_BLOCK_SIZE//4):
                for tile_x in range(INPUT_SUPER_BLOCK_SIZE//4):

                    # Fill in all tiles
                    tile = []
                    for ry in range(4):
                        for rx in range(4):
                            tile.append( (sb_x * INPUT_SUPER_BLOCK_SIZE + tile_x * 4 + rx, 
                                          sb_y * INPUT_SUPER_BLOCK_SIZE + tile_y * 4 + ry ) )

                    input_tiles.append(tile)

    return input_tiles

def hls_model():
    input_tiles = gen_input_stream()
    pprint(input_tiles)


    # DMA FIFO mimics a DMA engine that stores pixels from the bottom of a
    # super block so that it can be fetched at the start of a new super block
    # to include those pixels in downsampling
    dma_fifo        = []

    above_pixels    = []
    left_pixels     = []

    # Scan through all super blocks
    for sb_y in range(INPUT_HEIGHT//INPUT_SUPER_BLOCK_SIZE):
        for sb_x in range(INPUT_WIDTH//INPUT_SUPER_BLOCK_SIZE):

            # At the start if a new super block, fetch the bottom row
            # pixels of the super block that's above from the DMA FIFO.
            if sb_y != 0:
                for x in range(INPUT_SUPER_BLOCK_SIZE);
                    above_pixels[x] = dma_fifo[0] 
                    dma_fifo = dma_fifo[1:0]

            # Scan through all tiles
            for tile_y in range(INPUT_SUPER_BLOCK_SIZE//4):
                for tile_x in range(INPUT_SUPER_BLOCK_SIZE//4):

                    # pop a tile from input stream
                    input_tile  = input_tiles[0]
                    input_tiles = input_tiles[1:]

                    is_bottom_row_sb    = sb_y == INPUT_HEIGHT//INPUT_SUPER_BLOCK_SIZE-1
                    is_bottom_row_tile  = tile_y == INPUT_SUPER_BLOCK_SIZE//4-1 

                    # Feed the bottom pixels of a super block to the DMA FIFO.
                    # Since a tile is 4x4 pixels, this happens 4 pixels at a time.
                    if not(is_bottom_row_sb) and is_bottom_row_tile:
                        dma_fifo.append(input_tile[12:])

                    tile_lt_x   = sb_x * INPUT_SUPER_BLOCK_SIZE + tile_x * 4
                    tile_lt_y   = sb_y * INPUT_SUPER_BLOCK_SIZE + tile_y * 4


            
reference_model()
input_tiles = hls_model()

pprint(ref_output_pixels)


