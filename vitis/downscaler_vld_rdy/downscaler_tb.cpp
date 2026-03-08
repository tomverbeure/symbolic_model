#include <iostream>
#include "ap_axi_sdata.h"
#include "hls_stream.h"

#include "downscaler_impl.h"

// Reference the top-level function from your header or source
//typedef ap_axis<160, 0, 0, 0> t_tile;
//void downscaler(hls::stream<t_tile> &in_stream, hls::stream<t_tile> &out_stream);

int main() {
    hls::stream<t_tile> tile_in_chn;
    hls::stream<t_tile> tile_out_chn;
    int err_count = 0;

    std::cout << "--- Starting Stream Copier Testbench ---" << std::endl;

    const int nr_input_tiles    = INPUT_WIDTH * INPUT_HEIGHT / PIXELS_PER_TILE;

    // It's a 2:1 downscaler in both directions, so expect 4 times less pixels.
    const int nr_output_tiles   = INPUT_WIDTH * INPUT_HEIGHT / PIXELS_PER_TILE / 4;

    std::cout << "Sending " << nr_input_tiles << " input tiles" << std::endl;

    t_tile input_tile;

    // Send 16 pixels at a time
    for (int i = 0; i < nr_input_tiles; i++) {
        input_tile.data = i * 10; 
        input_tile.keep = -1;                     // All bytes valid
        input_tile.last = (i == nr_input_tiles-1) ? 1 : 0; // Assert TLAST on the last packet
        tile_in_chn.write(input_tile);
    }

    downscaler(tile_in_chn, tile_out_chn);

    std::cout << "Expecting " << nr_output_tiles << " output tiles" << std::endl;

    // 3. Verify Output Data
    if (tile_out_chn.size() != nr_output_tiles) {
        std::cout << "ERROR: Expected " << nr_output_tiles << " packets, but got " << tile_out_chn.size() << std::endl;
        return 1; 
    }

    for (int i = 0; i < nr_output_tiles; i++) {
        t_tile output_tile = tile_out_chn.read();
        std::cout << "Recv: " << output_tile.data << " | Expected: " << (i * 10) << std::endl;
        
        if (output_tile.data != (i * 10)) {
            err_count++;
        }
    }

    // 4. Final Status
    if (err_count == 0) {
        std::cout << "TEST PASSED!" << std::endl;
        return 0; // HLS interprets 0 as success
    } else {
        std::cout << "TEST FAILED with " << err_count << " errors." << std::endl;
        return 1; // HLS interprets non-zero as failure
    }
}
