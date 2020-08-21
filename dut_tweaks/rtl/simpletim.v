//-----------------------------------------------------------------------------
// Block: simpletim
// Description: creates a timer that is readable from from processor
// This block has an free-running counter that increments each clock cycle.
// When processor writes to capture register the counters register is
// latched.  The process can the read the latched count.
//
//------------------------------------------------------------------------------


module simpletim (
  input        clk,
  input        reset_n,
  inout  [7:0] data_out,
  input  [7:0] data_in,
  input        cs_n,
  input        rd_n,
  input        wr_n,
  input  [2:0] addr
);

  localparam BYTE0   = 0;
  localparam BYTE1   = 1;
  localparam BYTE2   = 2;
  localparam BYTE3   = 3;
  localparam CAPTURE = 4;

  wire read_sel = !cs_n & !rd_n & wr_n;
  wire write_sel = !cs_n & rd_n & !wr_n;

  wire capture = write_sel && addr==CAPTURE;
  reg  [31:0] cnt;
  reg  [31:0] cnt2;

  wire [7:0] bytes [0:3];
  assign bytes[0] = cnt2[7:0];
  assign bytes[1] = cnt2[15:8];
  assign bytes[2] = cnt2[23:16];
  assign bytes[3] = cnt2[31:24];
  assign data_out = read_sel ? bytes[ addr[1:0]  ] : 8'h0;

  always @(posedge clk or negedge reset_n) begin
    if (~reset_n) begin
      cnt  <= 'h0;
      cnt2 <= 'h0;
    end else begin
      cnt <= cnt + 1;
      if (capture) begin
        cnt2 <= cnt;
      end
    end
  end

endmodule





