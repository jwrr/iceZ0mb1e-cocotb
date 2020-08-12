# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Edge
from cocotb.triggers import FallingEdge
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from utils.dv_test import dv_test
from monitors.spi import SPIMonitor

from cocotb.monitors import Monitor
from cocotb.drivers import BitDriver
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory
from cocotb.scoreboard import Scoreboard



# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


#### @cocotb.test()
async def run_test(dut):

    en_gpio_loopback_test = True
    en_spi_test = True

    dv = dv_test(dut)


#     spi_io = {
#         'sclk' : dut.spi_sclk,
#         'cs_n' : dut.spi_cs,
#         'sdi'  : dut.spi_mosi,
#         'sdo'  : dut.spi_miso,
#     }
#     spi = SPIMonitor(dut=dut, io=spi_io)



    spi = SPIMonitor(
        dut=dut,
        arg = {
            'name' : "SPI Monitor",
            'size' : 8, # bits
            'mode' : 0,
            'lsb_first' : False,
        },
        io= {
            'sclk' : dut.spi_sclk,
            'cs_n' : dut.spi_cs,
            'sdi'  : dut.spi_mosi,
            'sdo'  : dut.spi_miso,
        }
    )


    expect_list = []
    spi.start(expect_list)
    clk = Clock(dut.clk, 10, units="ns")  # Create a 10us period clock on port clk
    cocotb.fork(clk.start())  # Start the clock

    dut.uart_txd = 0
    await FallingEdge(dut.clk)

    ### =============================================================================================================
    ### GPIO LOOPBACK TEST

    if en_gpio_loopback_test:
        dv.info("GPIO Loopback Test")
        for i in range(20000):
            await FallingEdge(dut.clk)
            dut.P2_in <= dut.P1_out.value
            try:
                gpio_value = int(dut.P1_out.value.binstr,2)
                loop_done = True if gpio_value == 0xff else False
            except ValueError:
                gpio_value = 0
                loop_done = False
            if (i+1) % 1000 == 0:
                dv.info("clock = " + str(i+1) +": P1_out = " + str(gpio_value) )
            if loop_done: break

        await Edge(dut.P1_out)

        gpio_result = int(dut.P1_out.value.binstr,2)
        if gpio_result == 0:
            dv.info("GPIO Loopback Test Passed")
        else:
            dv.info("GPIO Loopback Test Failed - Error Count = " + str(gpio_result) )

        dut.P1_in = 0
        await ClockCycles(dut.clk,100)


    ### =============================================================================================================
    ### SPI TEST

    if en_spi_test:
        dv.info("SPI Test (random modes and speeds)")
        random.seed(42)
        spi_val = "10010111";
        err_cnt = 0;
        toggle = 0
        for i in range(20):
            if i == 10:
                spi.stop()

            # SEND BYTE-VALUE TO SEND OVER SPI TO Z80 USING BPIO p2[7:0]
            expect = random.randrange(256) # 0x91 + i
            expect_list.append(expect)
            dut.P2_in.value = expect

            # SEND MODE AND CLKDIV TO Z80 OVER GPIO P1[7:0]
            # Bit [1:0] mode
            # Bit [2]   toggle (ensure p1_in changes)
            # Bit [6:3] clkdiv (div sys clk)
            # Bit [7]   done
            spi.mode = random.randrange(4) # i % 4
            clkdiv = random.randrange(0, 16, 2)
            toggle = (toggle + 4) & 0x04
            P1_in = (clkdiv << 3) | toggle | spi.mode
            dut.P1_in.value = P1_in

            # WAIT FOR Z80 TO SEND SsPI MESSAGE AND COMPARE WITH EXPECETD VALUE
            spi_val = await spi.peripheral( "{:08b}".format(i|0x80) )
            actual = int(spi_val, 2)
            result = "pass" if actual == expect else "FAIL"
            msg = "{} P1_in = {} clkdiv = {} mode = {} actual = {} expect = {}".format(
                  result, hex(P1_in), (clkdiv // 2), spi.mode, actual, expect )
            if result == "FAIL":
                err_cnt += 1
                dv.info(msg)
            else:
                dv.info(msg)

        dut.P1_in.value = 0x80
        if err_cnt == 0:
            dv.info("SPI Test Passed")
        else:
            dv.info("SPI Test Failed - Error Count = " + str(err_cnt) )

        await ClockCycles(dut.clk,100)

        # Print result of scoreboard.
        # raise tb.scoreboard.result


        ### =============================================================================================================

# Register the test.
factory = TestFactory(run_test)
factory.generate_tests()


## ================================================================
#
# def input_gen():
#     """Generator for input data applied by BitDriver.
#
#     Continually yield a tuple with the number of cycles to be on
#     followed by the number of cycles to be off.
#     """
#     while True:
#         yield random.randint(1, 5), random.randint(1, 5)
#
#
# class DFF_TB(object):
#     def __init__(self, dut, init_val):
#         """
#         Setup the testbench.
#
#         *init_val* signifies the ``BinaryValue`` which must be captured by the
#         output monitor with the first rising clock edge.
#         This must match the initial state of the D flip-flop in RTL.
#         """
#         # Some internal state
#         self.dut = dut
#         self.stopped = False
#
#         # Create input driver and output monitor
#         self.input_drv = BitDriver(signal=dut.d, clk=dut.c, generator=input_gen())
#         self.output_mon = BitMonitor(name="output", signal=dut.q, clk=dut.c)
#
#         # Create a scoreboard on the outputs
#         self.expected_output = [init_val]  # a list with init_val as the first element
#         self.scoreboard = Scoreboard(dut)
#         self.scoreboard.add_interface(self.output_mon, self.expected_output)
#
#         # Use the input monitor to reconstruct the transactions from the pins
#         # and send them to our 'model' of the design.
#         self.input_mon = BitMonitor(name="input", signal=dut.d, clk=dut.c,
#                                     callback=self.model)
#
#     def model(self, transaction):
#         """Model the DUT based on the input *transaction*.
#
#         For a D flip-flop, what goes in at ``d`` comes out on ``q``,
#         so the value on ``d`` (put into *transaction* by our ``input_mon``)
#         can be used as expected output without change.
#         Thus we can directly append *transaction* to the ``expected_output`` list,
#         except for the very last clock cycle of the simulation
#         (that is, after ``stop()`` has been called).
#         """
#         if not self.stopped:
#             self.expected_output.append(transaction)
#
#     def start(self):
#         """Start generating input data."""
#         self.input_drv.start()
#
#     def stop(self):
#         """Stop generating input data.
#
#         Also stop generation of expected output transactions.
#         One more clock cycle must be executed afterwards so that the output of
#         the D flip-flop can be checked.
#         """
#         self.input_drv.stop()
#         self.stopped = True
#
#
# async def run_test(dut):
#     """Setup testbench and run a test."""
#
#     cocotb.fork(Clock(dut.c, 10, 'us').start(start_high=False))
#
#     tb = DFF_TB(dut, init_val=BinaryValue(0))
#
#     clkedge = RisingEdge(dut.c)
#
#     # Apply random input data by input_gen via BitDriver for 100 clock cycles.
#     tb.start()
#     for _ in range(100):
#         await clkedge
#
#     # Stop generation of input data. One more clock cycle is needed to capture
#     # the resulting output of the DUT.
#     tb.stop()
#     await clkedge
#
#     # Print result of scoreboard.
#     raise tb.scoreboard.result
#
#
# # Register the test.
# factory = TestFactory(run_test)
# factory.generate_tests()



