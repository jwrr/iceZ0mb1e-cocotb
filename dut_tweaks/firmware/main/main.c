//
// iceZ0mb1e - FPGA 8-Bit TV80 SoC for Lattice iCE40
// with complete open-source toolchain flow using yosys and SDCC
//
// Copyright (c) 2018 Franz Neumann (netinside2000@gmx.de)
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the "Software"),
// to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense,
// and/or sell copies of the Software, and to permit persons to whom the
// Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
// IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
// CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
// TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
// SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
//

#include <stdint.h>
#include "mini-printf.h"
#include "icez0mb1e.h"
#include "cpu.h"
#include "uart.h"
#include "i2c.h"
#include "spi.h"
#include "ssd1306.h"
#include "simpletimer.h"

int8_t start = 0;
uint16_t last_usable_addr = 0;
int8_t free = 0;
char strbuf[80];

void Read_SPI_25L008A(uint8_t *buffer, uint16_t len)
{
    uint8_t spi_send[4] = {0x3, 0x00, 0x00, 0x00};

    spi_xfer(spi_send, buffer, 4, len);
}

void oled_reset()
{
    port_b = 0x00;
    delay(50000);
    port_b = 0x01;
    delay(50000);
    port_b = 0x00;
    delay(50000);
    port_b = 0x01;
    delay(50000);
}

void View_Memory(uint8_t *mem, uint16_t len)
{
    uint16_t x;

    for(x = 0; x < len; x++)
    {
        if((x%16) == 0)
        {
            snprintf(strbuf, sizeof(strbuf), "\r\n%04X: ", x);
            uart_write(strbuf);
        }
        snprintf(strbuf, sizeof(strbuf), "%02X", mem[x]);
        uart_write(strbuf);
    }

    snprintf(strbuf, sizeof(strbuf), "\r\n");
    uart_write(strbuf);
}


void blink(unsigned int hi, unsigned int low)
{
    port_a = 0xff; // bit 0 is LED
    timer_delay_ms(hi);

    port_a = 0x00;  // bit 0 is LED
    timer_delay_ms(low);
}

unsigned int wpm = 5;
unsigned int dit_time_ms = 240; // 5 wpm

// unsigned int dit_time_ms = 6*1000/(5*wpm);  

void dot() { blink(240, 240); }
void dash() { blink(3*240, 240); }
void endsym() { blink(0, 2*240); } // this is actually 3*dot
void endword() { blink(0, 6*240); } // this is actually 7*dot

void didah(const char* str)
{
    char c = ' ';
    for (int i=0; str[i]!='\0'; i++) {
        c = str[i];
        switch (c) {
            case '.': dot(); break;
            case '_': dash(); break;
            case ' ': endword(); break;
        }
    }
    if (c!=' ') endsym();
}


void morse(char* str)
{
/*
  di    = 1 unit
  dah   = 3*di
  intra_char_time = 1*di  -- time between dits,  dahs
  inter_char_time = 3*di  -- time between letters
  inter_word_time = 7*di  -- time between words
  word
  . = di+space   = 2
  _ = 2*di+space = 4
  s = 2*space    = 2 (this is really 3 spaces. the previous symbol includes a trailing space)
  w = 6*space    = 6 (this is really 7 spaces. the previous symbol includes a trailing space)
  paris = ".__.s._s._.s..s...w" = 2+4+4+2+2+ 2+4+2+ 2+4+2+2+ 2+2+2+ 2+2+2+6 = 14+8+10+6+12 = 50 
  
  1wpm = 1*paris/minute = 50 di / 60sec; Tdi = 1.2sec per di
  5wpm = (1.2sec/di) / 5 = 0.240sec/di
  13wpm = 1.2 / 13 = 0.092 sec/di
  20wpm = 1.2 / 20 = 0.06 sec/di
  
*/

    const char* letters[] = {
        "._",     // 0 a
        "_...",   // 1 b
        "_._.",   // 2 c
        "_..",    // 3 d
        ".",      // 4 e
        ".._.",   // 5 f
        "__.",    // 6 g
        "....",   // 7 h
        "..",     // 8 i
        ".___",   // 9 j
        "_._",    // 10 k
        "._..",   // 11 l
        "__",     // 12 m
        "_.",     // 13 n
        "___",    // 14 o
        ".__.",   // 15 p
        "__._",   // 16 q
        "._.",    // 17 r
        "...",    // 18 s
        "_",      // 19 t
        ".._",    // 20 u
        "..._",   // 21 v
        ".__",    // 22 w
        "_.._",   // 23 x
        "_.__",   // 24 y
        "__..",   // 25 z
        "_____",  // 26 0
        ".____",  // 27 1
        "..___",  // 28 2
        "...__",  // 29 3
        "...._",  // 30 4
        ".....",  // 31 5
        "_....",  // 32 6
        "__...",  // 33 7
        "___..",  // 34 8
        "____.",  // 35 9
        " "       // 36 end of word
//         "", // 0 .
//         "", // 0 ,
//         "", // 0 ?
//         "", // 0 '
//         "", // 0 !
//         "", // 0 /
//         "", // 0 (
//         "", // 0 )
//         "", // 0 &
//         "", // 0 :
//         "", // 0 ;
//         "", // 0 =
//         "", // 0 +
//         "", // 0 -
//         "", // 0 _
//         "", // 0 "
//         "", // 0 $
//         "", // 0 @
//         ""  // 0 (
    };

    for (int i=0; str[i]!='\0'; i++) {
        char c = str[i];
        unsigned int offset = 0;
        if ('A' <= c && c <= 'Z') {
            offset = c - 'A';
        } else if ('a' <= c && c <= 'z') {
            offset = c - 'a';
        } else if ('0' <= c && c <= '9') { // number
            offset = c - '0' + 26;
        } else if (c==' ') {
            offset = 36;
        } else {
            continue;
        }
        didah( letters[offset] );
    }
} // morse

void main ()
{
    uint16_t *addr;
    uint8_t buffer[64];
    int8_t uart_rx = 0;

/*
    // ========================================================================
    // GPIO LOOP-BACK TEST
    // Testbench connects P1_out to P2_in
    port_cfg = 0x02; // P2=input P1=output
    uint16_t err = 0;
    for (uint8_t ii=0; 1; ii++) {
        port_a = ii;
        if (port_b != ii) err++;
        if (ii==255) break;
    }
    port_a = err;
    // ========================================================================

    uint8_t val = 0;
    for (uint8_t i2=0; i2<20; i2++) val = port_a; // delay between tests


    // ========================================================================
    // SPI TEST

    port_cfg = 0x3; // port_a contains mode (bit 7 id done), port_b contains data
    uint8_t mode = 0;
    uint8_t speed = 6;
    while (1) {
        uint8_t a = port_a;
        if (a & 0x80) break;  // bit[7] = done
        speed = (a >> 3) & 0x0F;
        mode = a & 0x03;
        spi_config(mode, speed);
        spi_xfer_single(port_b);
    }


   timer_cfg = 1;  // init
   timer_del0 = 0x24;
   timer_del1 = 0xf4;
   timer_del2 = 0;
   timer_del3 = 0;
   while (1) {
       timer_cfg = 3; // start
       while (timer_busy);
   }

asdfasdf */


    // ========================================================================

    port_cfg = 0x0; // make both io ports output
    port_a = 0x55;

    timer_start();
    while (1) {
        for (int i=0; i<5; i++) morse("paris "); // send message 5 times
        timer_delay_ms(10000); // wait 10 seconds between messages
    }
    timer_stop();


    // ========================================================================

/*


    //Initialize:
    uart_initialize(9600);
    spi_config(0, 12); //1MHz
    i2c_config(120); //100kHz

    //i2c Test:
    i2c_read_buf(0x5C, buffer, 5); // DHT12
    View_Memory(buffer, 5);
    i2c_read_buf(0x68, buffer, 20); // PCF8523
    View_Memory(buffer, 20);

    //SPI Test
    Read_SPI_25L008A(buffer, 64); // 25L008A
    View_Memory(buffer, 64);

    //I2C OLED display test:
    oled_reset();
    ssd1306_initialize(0x3C);
    ssd1306_clear();
    ssd1306_write(0, 0, "iceZ0mb1e SoC");
    ssd1306_write(2, 0, "by abnoname");
    ssd1306_write(3, 0, "0123456789 Test");
    ssd1306_write(4, 0, "Framebuffer On");
#ifdef SSD1306_ENABLE_FRAMEBUFFER
    ssd1306_update();
#endif
#ifdef SSD1306_ENABLE_GRAPHIC
    ssd1306_line(0, 48, 127, 63, 1);
    ssd1306_box(0, 127, 48, 63, 1);
    ssd1306_update();
#endif

    //Port test
    port_a = 0x02;

    //UART Test
    snprintf(strbuf, sizeof(strbuf), "iceZ0mb1e SoC by abnoname\r\n");
    uart_write(strbuf);

    //UART Terminal
    while(1)
    {
        uart_rx = getchar();

        switch(uart_rx)
        {
            case 'a':
                port_a = getchar();
                snprintf(strbuf, sizeof(strbuf), "port_a = 0x%X\n\r", port_a);
                uart_write(strbuf);
                break;
            case 'b':
                port_b = getchar();
                snprintf(strbuf, sizeof(strbuf), "port_b = 0x%X\n\r", port_b);
                uart_write(strbuf);
                break;
            case 'r':
                cpu_reset();
                break;
            case 'c':
                View_Memory((uint8_t*)SYS_ROM_ADDR, SYS_ROM_SIZE);
                break;
            case 'm':
                View_Memory((uint8_t*)SYS_RAM_ADDR, SYS_RAM_SIZE);
                break;
            case 't':
                //RAM Test
                last_usable_addr = 0;
                addr = &free;
                while((uint16_t)addr < (SYS_RAM_ADDR+SYS_RAM_SIZE))
                {
                    *(addr) = (uint16_t)addr;
                    if(*(addr) != addr)
                    {
                        break;
                    }
                    last_usable_addr = (uint16_t)addr;
                    addr++;
                }
                snprintf(strbuf, sizeof(strbuf), "RAM: start = 0x%X, last usable = 0x%X, ramsize = %u\n\r",
                    (uint16_t)&start, last_usable_addr, last_usable_addr-(uint16_t)&start
                );
                uart_write(strbuf);
                break;
            default:
                putchar(uart_rx);
                break;
        }
    }

asdfasdf */

}
