#include <iostream>
#include "ap_axi_sdata.h"
#include "hls_stream.h"

// Reference the top-level function from your header or source
typedef ap_axis<160, 0, 0, 0> t_tile;
void downscaler(hls::stream<t_tile> &in_stream, hls::stream<t_tile> &out_stream);

int main() {
    hls::stream<t_tile> tb_in;
    hls::stream<t_tile> tb_out;
    t_tile test_pkt;
    int err_count = 0;

    std::cout << "--- Starting Stream Copier Testbench ---" << std::endl;

    // 1. Prepare Input Data (Simulating 10 packets)
    for (int i = 0; i < 10; i++) {
        test_pkt.data = i * 10; // Simple pattern: 0, 10, 20...
        test_pkt.keep = -1;     // All bytes valid
        test_pkt.last = (i == 9) ? 1 : 0; // Assert TLAST on the last packet
        tb_in.write(test_pkt);
    }

    // 2. Call the HLS Function
    // In a real hardware loop, this would run continuously. 
    // Here we call it 10 times to process the 10 inputs.
    for (int i = 0; i < 10; i++) {
        downscaler(tb_in, tb_out);
    }

    // 3. Verify Output Data
    if (tb_out.size() != 10) {
        std::cout << "ERROR: Expected 10 packets, but got " << tb_out.size() << std::endl;
        return 1; 
    }

    for (int i = 0; i < 10; i++) {
        t_tile result = tb_out.read();
        std::cout << "Recv: " << result.data << " | Expected: " << (i * 10) << std::endl;
        
        if (result.data != (i * 10)) {
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