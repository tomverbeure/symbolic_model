#! /usr/bin/env python3

from pprint import pprint
from dataclasses import dataclass

debug   = False

INPUT_WIDTH             = 64
INPUT_HEIGHT            = 64
INPUT_SB_SIZE           = 16

# Some constraints to reduce the number of corner cases
assert INPUT_WIDTH % INPUT_SB_SIZE == 0
assert INPUT_HEIGHT % INPUT_SB_SIZE == 0
assert INPUT_SB_SIZE % 8 == 0

OUTPUT_WIDTH            = INPUT_WIDTH//2
OUTPUT_HEIGHT           = INPUT_HEIGHT//2
OUTPUT_SB_SIZE          = INPUT_SB_SIZE//2

@dataclass
class Pixel:
    x: int
    y: int


# Output: ref_output_pixels
#
# key: (x,y) coordinate, one for each pixel of the output image
# value: list with input pixel coordinates. The list is sorted
#        in left-to-right, then top-to-bottom scan order.
#        When an input pixel is used multiple times due to
#        picture boundary duplication then it has multiple
#        entries.
def reference_model():
    ref_output_pixels       = {}

    for y in range(OUTPUT_HEIGHT):
        for x in range(OUTPUT_WIDTH):
            ref_output_pixels[ (x,y) ] = []


            # x/y loop that gathers all the input pixels of
            # a 3x3 rectangle
            for sy in range(2*y-1, 2*y+2):
                for sx in range(2*x-1, 2*x+2):

                    # When accessing input pixels outside of the picture, clamp
                    # to use boundary pixels instead.
                    if sy<0:
                        sy_final = 0
                    elif sy >= INPUT_HEIGHT:
                        sy_final = INPUT_HEIGHT-1
                    else:
                        sy_final = sy

                    if sx<0:
                        sx_final = 0
                    elif sx >= INPUT_WIDTH:
                        sx_final = INPUT_WIDTH-1
                    else:
                        sx_final = sx

                    ref_output_pixels[ (x,y) ].append( Pixel(sx_final,sy_final) )

            if debug:
                print(f"ref ({x},{y}) => {ref_output_pixels[ (x,y) ]}")

    return ref_output_pixels

def gen_input_stream():
    # Generate a list with input pixels, super block by super block, then
    # in tiles of 4x4 pixels

    input_tiles     = []

    # Scan through all super blocks
    for sb_y in range(INPUT_HEIGHT//INPUT_SB_SIZE):
        for sb_x in range(INPUT_WIDTH//INPUT_SB_SIZE):

            # Scan through all tiles
            for tile_y in range(INPUT_SB_SIZE//4):
                for tile_x in range(INPUT_SB_SIZE//4):

                    # Fill in all tiles with 4x4 pixels
                    tile = []
                    for ry in range(4):
                        for rx in range(4):
                            tile.append( Pixel(sb_x * INPUT_SB_SIZE + tile_x * 4 + rx, 
                                               sb_y * INPUT_SB_SIZE + tile_y * 4 + ry ) )

                    input_tiles.append(tile)

    return input_tiles

def hw_model():
    input_tiles     = gen_input_stream()
    output_tiles    = []

    #pprint(input_tiles)

    # DMA FIFO mimics a DMA engine that stores pixels from the bottom of a
    # super block so that it can be fetched at the start of a new super block
    # to include those pixels in downsampling
    dma_fifo            = []

    above_left_pixel    = None
    above_pixels        = [ None ] * (INPUT_SB_SIZE // 2)
    left_pixels         = [ None ] * (INPUT_SB_SIZE * 3 // 4)

    output_merge_fifo   = [ ]

    tile_left_pixels    = [ None ] * 3
    tile_above_pixels   = [ None ] * 2

    output_tile         = [ None ] * 16

    # Scan through all super blocks
    for sb_y in range(INPUT_HEIGHT//INPUT_SB_SIZE):
        for sb_x in range(INPUT_WIDTH//INPUT_SB_SIZE):

            if debug:
                print(f"start of SB ({sb_x},{sb_y})")

            # At the start if a new super block, fetch the bottom row
            # pixels of the super block that's above from the DMA FIFO.
            # The top row of super blocks doesn't have above neighbors
            # so there's no DMA data. 
            if sb_y != 0:
                for x in range(INPUT_SB_SIZE//4):
                    above_pixels[2 * x    ] = dma_fifo[0][0]
                    above_pixels[2 * x + 1] = dma_fifo[0][1]
                    dma_fifo = dma_fifo[1:]

                    if debug:
                        print("pop fifo:")
                        pprint(above_pixels[x])

            # Scan through all tiles within a super block
            for tile_y in range(INPUT_SB_SIZE//4):

                for tile_x in range(INPUT_SB_SIZE//4):

                    # pop the current input tile from input stream
                    input_tile  = input_tiles[0]
                    input_tiles = input_tiles[1:]

                    is_bottom_row_sb    = sb_y == INPUT_HEIGHT//INPUT_SB_SIZE-1
                    is_bottom_row_tile  = tile_y == INPUT_SB_SIZE//4-1 
                    is_right_col_tile   = tile_x == INPUT_SB_SIZE//4-1

                    if debug:
                        tile_lt_x   = sb_x * INPUT_SB_SIZE + tile_x * 4
                        tile_lt_y   = sb_y * INPUT_SB_SIZE + tile_y * 4
                        print(f"start of tile ({tile_x},{tile_y}): ({tile_lt_x},{tile_lt_y})")

                    if sb_x == 0 and sb_y == 0 and tile_x == 0 and tile_y == 0:
                        above_left_pixel    = input_tile[0]

                    if debug:
                        print("above_left_pixel:")
                        pprint(above_left_pixel)
                    
                    # tile_left_pixels only needs to be initialized at the left boundary
                    # of a super block. For all other cases, it is updated below when
                    # the current tile calculations are completed.
                    if tile_x == 0:
                        if sb_x == 0:
                            tile_left_pixels[0] = ( input_tile[0], input_tile[4] )  
                            tile_left_pixels[1] = ( input_tile[4], input_tile[8], input_tile[12] ) 
                            tile_left_pixels[2] = input_tile[12]
                        else:
                            tile_left_pixels[0] = left_pixels[tile_y * 3]
                            tile_left_pixels[1] = left_pixels[tile_y * 3 + 1]
                            tile_left_pixels[2] = left_pixels[tile_y * 3 + 2]

                    if debug:
                        print("tile_left_pixels:")
                        pprint(tile_left_pixels)

                    if sb_y == 0 and tile_y == 0:
                        tile_above_pixels[0]    = (above_left_pixel, input_tile[0], input_tile[1] )
                        tile_above_pixels[1]    = (input_tile[1], input_tile[2], input_tile[3] )
                    else:
                        tile_above_pixels[0]    = above_pixels[tile_x * 2]
                        tile_above_pixels[1]    = above_pixels[tile_x * 2 + 1]

                    if debug:
                        print("tile_above_pixels:")
                        pprint(tile_above_pixels)

                    # Symbolic value of the 2x2 pixels that are filtered down from the 4x4 tile.
                    # The elements in the list for each output represent the terms that are summed.
                    # Each term can either be a pixel value (when it's input_tile[x]) or an intermediate sum
                    # (when it's tile_above_pixels[x] or tile_left_pixels[x])
                    p00 = (                      tile_above_pixels[0], 
                            tile_left_pixels[0], input_tile[0], input_tile[1], 
                                                 input_tile[4], input_tile[5] )

                    p10 = (                      tile_above_pixels[1], 
                            input_tile[ 1],      input_tile[ 2], input_tile[ 3] , 
                            input_tile[ 5],      input_tile[ 6], input_tile[ 7] ) 

                    p01 = (tile_left_pixels[1],  input_tile[ 4], input_tile[ 5] , 
                                                 input_tile[ 8], input_tile[ 9] , 
                                                 input_tile[12], input_tile[13] ) 

                    p11 = ( input_tile[ 5],      input_tile[ 6], input_tile[ 7] , 
                            input_tile[ 9],      input_tile[10], input_tile[11] , 
                            input_tile[13],      input_tile[14], input_tile[15] ) 

                    if tile_y & 1 == 0:
                        # Even rows of output pixels can't be sent to the output: they need to
                        # be merged with output pixels from the next row, so store them in a FIFO.
                        output_merge_fifo.append( (p00, p10, p01, p11) )
                    else:
                        # For odd rows, pop pixels from the precious row and fill in 
                        # the output tile.
                        # This happens in 2 phases: the left 2x4 part of the tile and then 
                        # the right part. This is done to reflect the hardware behavior where you
                        # can only fetch 1 element from a FIFO at time.
                        prev_p  = output_merge_fifo[0]
                        output_merge_fifo = output_merge_fifo[1:]

                        if tile_x & 1 == 0:
                            # Top-left 2x2
                            output_tile[0]  = prev_p[0]
                            output_tile[1]  = prev_p[1]
                            output_tile[4]  = prev_p[2]
                            output_tile[5]  = prev_p[3]

                            # Bottom-left 2x2
                            output_tile[8]  = p00
                            output_tile[9]  = p10
                            output_tile[12] = p01
                            output_tile[13] = p11
                        else:
                            # Top-right 2x2
                            output_tile[2]  = prev_p[0]
                            output_tile[3]  = prev_p[1]
                            output_tile[6]  = prev_p[2]
                            output_tile[7]  = prev_p[3]

                            # Bottom-right 2x2
                            output_tile[10]  = p00
                            output_tile[11]  = p10
                            output_tile[14]  = p01
                            output_tile[15]  = p11

                            output_tiles.append(output_tile)

                            # Invalidating the contents of an output tile isn't strictly
                            # required since it will be overwritten anyway by the correct data,
                            # but it makes debugging easier.
                            output_tile     = [ None ] * 16

                    # The bottom pixels of the current tile become the above pixels
                    # of the tile below it.
                    above_pixels_nxt        = [ None ] * 2
                    above_pixels_nxt[0]     = (tile_left_pixels[2], input_tile[12], input_tile[13] )
                    above_pixels_nxt[1]     = (input_tile[13], input_tile[14], input_tile[15] )

                    above_pixels[tile_x * 2]        = above_pixels_nxt[0]
                    above_pixels[tile_x * 2 + 1]    = above_pixels_nxt[1]

                    # The above_pixels array needs to be restored at the start of
                    # each super blocks so send those values to the DMA FIFO.
                    if not(is_bottom_row_sb) and is_bottom_row_tile:
                        dma_fifo.append(above_pixels_nxt)

                        if debug:
                            print("push fifo:")
                            pprint(above_pixels_nxt)
                    
                    # The right pixels of the current tile becomes the left pixels
                    # of the tile to the right of it.
                    tile_left_pixels[0] = ( input_tile[3], input_tile[ 7] )
                    tile_left_pixels[1] = ( input_tile[7], input_tile[11], input_tile[15] )
                    tile_left_pixels[2] = ( input_tile[15] )

                    if is_right_col_tile:
                        left_pixels[tile_y * 3]     = tile_left_pixels[0]
                        left_pixels[tile_y * 3 + 1] = tile_left_pixels[1]
                        left_pixels[tile_y * 3 + 2] = tile_left_pixels[2]

                    if sb_y == 0 and tile_y == 0:
                        above_left_pixel    = input_tile[3]

    assert len(dma_fifo) == 0
    assert len(output_merge_fifo) == 0

    return output_tiles

def sort_pixel_terms(input_pixel):
    output_pixel = sorted(input_pixel, key=lambda p: p.x + p.y*OUTPUT_WIDTH)
    return output_pixel

def flatten_terms(input_terms):
    output_terms = []

    for term in input_terms:
        if type(term) == list or type(term) == tuple:
            output_terms = output_terms + flatten_terms(term)
        else:
            output_terms.append(term)

    return output_terms

def flatten_tiles(input_tiles):

    output_tiles = []

    for input_tile in input_tiles:

        assert len(input_tile) == 16

        output_tile = []

        for input_pixel in input_tile:
            output_pixel = flatten_terms(input_pixel)

            if debug:
                print("input:")
                pprint(input_pixel)
                print("output:")
                pprint(output_pixel)

            sorted_output_pixel = sort_pixel_terms(output_pixel)
            output_tile.append(sorted_output_pixel)

        assert len(output_tile) == 16
        output_tiles.append(output_tile)

    return output_tiles

def compare_ref_hw(ref_output_pixels, input_tiles):

    for sb_y in range(OUTPUT_HEIGHT//OUTPUT_SB_SIZE):
        for sb_x in range(OUTPUT_WIDTH//OUTPUT_SB_SIZE):

            if debug:
                print(f"start of SB ({sb_x},{sb_y})")

            # Scan through all tiles
            for tile_y in range(OUTPUT_SB_SIZE//4):

                for tile_x in range(OUTPUT_SB_SIZE//4):

                    # pop a tile from hw tiles
                    input_tile    = input_tiles[0]
                    input_tiles   = input_tiles[1:]

                    for ry in range(4):
                        for rx in range(4):
                            coord_x = (sb_x * OUTPUT_SB_SIZE) + (tile_x * 4) + rx
                            coord_y = (sb_y * OUTPUT_SB_SIZE) + (tile_y * 4) + ry

                            # For tiles that are at the top or left boundary if the image,
                            # the sorted hw values won't always be in scan-order. 
                            # Sort the reference value the same way as the hw value so that
                            # they match.
                            ref_value_orig  = ref_output_pixels[ (coord_x, coord_y) ]
                            ref_value   = sort_pixel_terms(ref_value_orig)
                            
                            hw_value    = input_tile[ rx + ry * 4]

                            # 3x3 filter kernal has 9 inputs
                            for i in range(9):
                                if (ref_value[i].x != hw_value[i].x) or (ref_value[i].y != hw_value[i].y):
                                    print(f"MISMATCH! sb({sb_x},{sb_y}) tile({tile_x},{tile_y}) ({rx},{ry}) {i}")

                                    print("ref:")
                                    pprint(ref_value)
                                    print("hw:")
                                    pprint(hw_value)
                                    print("ref orig:")
                                    pprint(ref_value_orig)
                                    assert False

    print("PASS!")

ref_output_pixels   = reference_model()
hw_output_tiles     = hw_model()

if debug:
    print("hw tiles not flattened:")
    pprint(hw_output_tiles)

hw_output_tiles = flatten_tiles(hw_output_tiles)

if debug:
    print("hw tiles flattened:")
    pprint(hw_output_tiles)

compare_ref_hw(ref_output_pixels, hw_output_tiles)

