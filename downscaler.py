#! /usr/bin/env python3

debug   = False

INPUT_WIDTH	            = 32
INPUT_HEIGHT	        = 32
INPUT_SUPER_BLOCK_SIZE  = 82

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
            
reference_model()


