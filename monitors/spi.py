# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.triggers import Edge
from cocotb.triggers import FallingEdge
from cocotb.triggers import RisingEdge
from cocotb.triggers import First
from cocotb.monitors import Monitor

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class SPIMonitor(Monitor):

    #   mode cpol cpha
    #    0    0    0    drive on falling sample on rising;  sclk=0 when idle
    #    1    0    1    drive on rising  sample on falling; sclk=0 when idle
    #    2    1    1    drive on rising  sample on falling; sclk=1 when idle
    #    3    1    0    drive on falling sample on rising;  sclk=1 when idle

    def __init__(self, dut, arg={}, io={}, callback=None, event=None):
        self.dut = dut
        self.io = io
        self.name = arg['name'] if arg and arg['name'] else 'SPI Monitor'
        self.size = arg['size'] if arg and arg['size'] else 8 # bits
        self.lsb_first = arg['lsb_first'] if arg and arg['lsb_first'] else False
        self.mode = arg['mode'] if arg and arg['mode'] else 0
#         self.callback = arg['callback'] if arg and arg['callback'] else None
#         self.event = arg['event'] if arg and arg['event'] else None
        self.sclk_re = RisingEdge(self.io['sclk'])
        self.sclk_fe = FallingEdge(self.io['sclk'])
        self.cs_n_edge = Edge(self.io['cs_n']) if self.io['cs_n'] is not None else None
        Monitor.__init__(self, callback, event)

        
    async def peripheral(self, sdo_binstr):
        sdi_binstr = ""
        if self.io['cs_n'] is not None: # some 2-wire point-to-points do not have cs
            await FallingEdge(self.io['cs_n'])
        if self.lsb_first:
            sdo_binstr = sdo_binstr[::-1]  # data bits sent from left to right
        send_edge = None
        if self.io['sdo'] is not None: # some 2-wire implementations are write only
            send_edge = self.sclk_fe if self.mode in [0, 3] else self.sclk_re
        capture_edge  = self.sclk_re if self.mode in [0, 3] else self.sclk_fe
        if self.mode in [0, 2] and self.io['sdo'] is not None:
            self.io['sdo'] <= int(sdo_binstr[0], 2) # drive before 1st clock
            sdo_binstr = sdo_binstr[1:] # remove bit 0 (left-most bit)
        while len(sdi_binstr) < self.size:
            edge = await First(self.cs_n_edge, capture_edge, send_edge)
            if edge == self.cs_n_edge:
                break
            elif edge == capture_edge:
                sdi_binstr = sdi_binstr + self.io['sdi'].value.binstr
            elif sdo_binstr != "": # Send Edge. Check if data is available
                self.io['sdo'] <= int(sdo_binstr[0], 2)
                sdo_binstr = sdo_binstr[1:] # remove bit 0 (left-most bit)
        if self.lsb_first:
           sdi_binstr = sdi_binstr[::-1]
        return sdi_binstr


    async def _monitor_recv(self):
        spi_val = "{:08b}".format(0)
        while True:
            spi_val = await self.peripheral(spi_val)
            self._recv(spi_val)


    async def fake_scoreboard(self, expect_list):
        self.enable_scoreboard = True
        self.expect_list = expect_list
        log = self.dut._log
        i = 0
        spi_val = "{:08b}".format(0)
        while self.enable_scoreboard:
            spi_val = await self.peripheral(spi_val)
            try:
                actual = int(spi_val, 2)
                expect = expect_list[i]
                if actual == expect:
                   log.info("pass: actual = {} expect = {} - {}".format(actual, expect, self.name) )
                else:
                   log.error("FAIL: actual = {} expect = {} - {}".format(actual, expect, self.name) )
                
            except ValueError:
                log.error("FAIL: actual = {} expect = {} - X Detected in {}".format(spi_val, expect, self.name ) )
            i += 1
            

    def start(self, expect_list):
        cocotb.fork(self.fake_scoreboard(expect_list))


    def stop(self):
        self.enable_scoreboard = False
        

        


