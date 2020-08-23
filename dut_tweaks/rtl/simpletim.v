//-----------------------------------------------------------------------------
// Block: simpletim
// Description: creates a timer that is readable from from processor
// This block has an free-running counter that increments each clock cycle.
// When processor writes to capture register the counters register is
// latched.  The process can the read the latched count.
//
// The timer is 32 bits. At 16MHz it rolls over at about 4.5 minutes.
//
//------------------------------------------------------------------------------
/*
   tim_cfg = 1;  // init
   while (1) {
       tim_wait 0,1,2,3;
       tim_cfg = 2; // start
       while (tim_busy);
   }
*/   


module simpletim (
    input         clk,
    input         reset_n,
    output  [7:0] data_out,
    input   [7:0] data_in,
    input         cs_n,
    input         rd_n,
    input         wr_n,
    input   [3:0] addr
);

    localparam TIM_WAIT0   = 0;
    localparam TIM_WAIT1   = 1;
    localparam TIM_WAIT2   = 2;
    localparam TIM_WAIT3   = 3;

    // Register TIM_CFG - 6'b0, latch, compare}
    localparam TIM_CFG  = 4; // {7'b0, compare}

    // compare - start comparing the timer value with the value loaded into the
    //           32-bit match register.
    // latch   - since only one TIM_CURR is read at a time, there is  chance of
    //           roll-over while reading the 32-bit value. The prevent this set
    //           rd=1 to latch the timer value into a shadow register and then
    //           read the shadow reg.
    //

    localparam TIM_BUSY   = 5;

    localparam TIM_CURR0   = 6;
    localparam TIM_CURR1   = 7;
    localparam TIM_CURR2   = 8;
    localparam TIM_CURR3   = 9;

    wire read_sel  = !cs_n & !rd_n &  wr_n;
    wire write_sel = !cs_n &  rd_n & !wr_n;

    wire set_wait_duration0_pulse    = write_sel && addr==TIM_WAIT0;
    wire set_wait_duration1_pulse    = write_sel && addr==TIM_WAIT1;
    wire set_wait_duration2_pulse    = write_sel && addr==TIM_WAIT2;
    wire set_wait_duration3_pulse    = write_sel && addr==TIM_WAIT3;
    
    wire timer_init_pulse  = write_sel && addr==TIM_CFG && data_in[0];
    wire timer_start_pulse = write_sel && addr==TIM_CFG && data_in[1];
    wire timer_read_status = read_sel  && addr==TIM_BUSY;

    reg         timer_busy;
    reg  [31:0] timer_cnt;
    reg  [31:0] shadow_cnt;
    reg  [31:0] wait_duration;
    reg  [31:0] done_cnt;

    reg   [7:0] data_out;
    always@(*) begin
        if (~read_sel)
            data_out <= 8'b0;
        else begin
            case (addr)
                TIM_WAIT0 : data_out <= shadow_cnt[0*8 +: 8];
                TIM_WAIT1 : data_out <= shadow_cnt[1*8 +: 8];
                TIM_WAIT2 : data_out <= shadow_cnt[2*8 +: 8];
                TIM_WAIT3 : data_out <= shadow_cnt[3*8 +: 8];

                TIM_CFG   : data_out <= 8'b0;
                TIM_BUSY  : data_out <= {7'b0, timer_busy};

                TIM_CURR0 : data_out <= wait_duration[0*8 +: 8];
                TIM_CURR1 : data_out <= wait_duration[1*8 +: 8];
                TIM_CURR2 : data_out <= wait_duration[2*8 +: 8];
                TIM_CURR3 : data_out <= wait_duration[3*8 +: 8];
                
                default : data_out <= 8'b0;
            endcase
        end
    end

    always @(posedge clk or negedge reset_n) begin
        if (~reset_n) begin
            timer_cnt      <= 32'h0;
            shadow_cnt     <= 32'h0;
            done_cnt       <= 32'h0;
            wait_duration  <= 32'h0;
            timer_busy     <= 1'b0;
        end else begin
            timer_cnt <= timer_init_pulse ? 'h0 : timer_cnt + 1;

            // capture the timer value whenever processor reads status
            if (timer_read_status) shadow_cnt <= timer_cnt;

            if (set_wait_duration0_pulse) wait_duration[0*8 +: 8] = data_in;
            if (set_wait_duration1_pulse) wait_duration[1*8 +: 8] = data_in;
            if (set_wait_duration2_pulse) wait_duration[2*8 +: 8] = data_in;
            if (set_wait_duration3_pulse) wait_duration[3*8 +: 8] = data_in;

            if (timer_init_pulse) begin
                timer_busy <= 1'b0;
                done_cnt <= 'h0;
            end else if (timer_start_pulse) begin
                timer_busy <= 1'b1;
                done_cnt <= done_cnt + wait_duration;
            end else if (timer_busy && (timer_cnt == done_cnt) ) begin
                timer_busy <= 1'b0;
            end

        end // else if n
    end // always

endmodule






