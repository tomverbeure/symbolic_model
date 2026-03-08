#include "ap_axi_sdata.h"
#include "hls_stream.h"

// Define a 160-bit wide AXI-Stream packet: 16 pixels, 10bpp
typedef ap_axis<160, 0, 0, 0> t_tile;

void downscaler(hls::stream<t_tile> &in_stream, hls::stream<t_tile> &out_stream) {
    #pragma HLS INTERFACE axis port=in_stream
    #pragma HLS INTERFACE axis port=out_stream
    #pragma HLS INTERFACE ap_ctrl_none port=return

    t_tile temp;

    // Read from the input and write to the output
    // HLS handles the handshake (TREADY/TVALID) automatically
    //if (!in_stream.empty()) {
    {    
        in_stream.read(temp);
        out_stream.write(temp);
    }
}