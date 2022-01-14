#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-09 hd44780.py

# HD44780 with PCF8574 piggyback I2C driver
# Data from:
#  https://www.sparkfun.com/datasheets/LCD/HD44780.pdf

# Assumed pinout:
# PCF8574     P0  P1  P2  P3  P4  P5  P6  P7
# HD44780     RS  RW   E  BL  D4  D5  D6  D7


# contol masks

LCD_CTRL_RS             = 0b00000001
LCD_CTRL_RW             = 0b00000010
LCD_CTRL_ENABLE         = 0b00000100
LCD_CTRL_BACKLIGHT      = 0b00001000

# command masks

LCD_CMD_CLEAR_DISPLAY   = 0b00000001
LCD_CMD_CURSOR_HOME     = 0b00000010
LCD_CMD_ENTRY_MODE      = 0b00000100
LCD_CMD_DISPLAY_CTRL    = 0b00001000
LCD_CMD_CS_SHIFT        = 0b00010000
LCD_CMD_FUNCTION_SET    = 0b00100000
LCD_CMD_SET_CGRAM_ADDR  = 0b01000000
LCD_CMD_SET_DDRAM_ADDR  = 0b10000000

# entry mode command options

LCD_OPT_NTRY_CDEC       = 0b00000000
LCD_OPT_NTRY_CINC       = 0b00000010
LCD_OPT_NTRY_DSHIFT_OFF = 0b00000000
LCD_OPT_NTRY_DSHIFT_ON  = 0b00000001

# display control command options

LCD_OPT_DISP_DOFF       = 0b00000000
LCD_OPT_DISP_DON        = 0b00000100
LCD_OPT_DISP_COFF       = 0b00000000
LCD_OPT_DISP_CON        = 0b00000010
LCD_OPT_DISP_BOFF       = 0b00000000
LCD_OPT_DISP_BON        = 0b00000001

# function set command options

LCD_OPT_FUNC_DL_4BIT    = 0b00000000
LCD_OPT_FUNC_DL_8BIT    = 0b00010000
LCD_OPT_FUNC_N_1LINE    = 0b00000000
LCD_OPT_FUNC_N_2LINE    = 0b00001000
LCD_OPT_FUNC_FONT_5X8   = 0b00000000
LCD_OPT_FUNC_FONT_5X10  = 0b00000100

# display data ram address offsets

LCD_OFFSET_LINE1        = 0x00
LCD_OFFSET_LINE2        = 0x40
LCD_OFFSET_LINE3        = 0x14
LCD_OFFSET_LINE4        = 0x54


class HD44780:

  def __init__(self, xm, xt, addr=0x27):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    # init 

    self._send_byte(LCD_CMD_FUNCTION_SET | LCD_OPT_FUNC_DL_8BIT | 0x03)
    self._send_byte(LCD_CMD_FUNCTION_SET | LCD_OPT_FUNC_DL_8BIT | 0x02)

    # function set 4-bit mode, 2 line mode, 5x8 font

    self._send_byte(LCD_CMD_FUNCTION_SET | LCD_OPT_FUNC_DL_4BIT | LCD_OPT_FUNC_N_2LINE | LCD_OPT_FUNC_FONT_5X8)

    # cursor home

    self._send_byte(LCD_CMD_CURSOR_HOME)

    # display control on, cursor off, blink off

    self._send_byte(LCD_CMD_DISPLAY_CTRL | LCD_OPT_DISP_DON | LCD_OPT_DISP_COFF | LCD_OPT_DISP_BOFF)

    # entry mode, increment cursor, no display shift

    self._send_byte(LCD_CMD_ENTRY_MODE | LCD_OPT_NTRY_CINC | LCD_OPT_NTRY_DSHIFT_OFF)

    # clear

    self._send_byte(LCD_CMD_CLEAR_DISPLAY)


  def _send_byte(self, byte, data=False, backlight=True):

    # split byte into halves

    half1 = byte & 0xF0
    half2 = (byte << 4) & 0xF0

    # set data mask

    dmask = LCD_CTRL_RS if data else 0x00

    # set backlight mask

    bmask = LCD_CTRL_BACKLIGHT if backlight else 0x00

    # write halves

    for half in [half1, half2]:

      half = half | dmask | bmask

      # pulse clock/enable cycle

      self._xm.i2c_write_byte(self._addr, half | LCD_CTRL_ENABLE)

      self._xt.sleep_ms(1)

      self._xm.i2c_write_byte(self._addr, half & ~LCD_CTRL_ENABLE)

      if half == half1:
        self._xt.sleep_ms(1)

    if not data and (byte == LCD_CMD_CLEAR_DISPLAY or byte == LCD_CMD_CURSOR_HOME):
      self._xt.sleep_ms(5)


  def show(self, text, line):

    if not isinstance(text, str):
      return False

    if not isinstance(line, int) or line < 1 or line > 4:
      return False

    offset = 0x00

    if line == 1:
      offset = LCD_OFFSET_LINE1
    elif line == 2:
      offset = LCD_OFFSET_LINE2
    elif line == 3:
      offset = LCD_OFFSET_LINE3
    elif line == 4:
      offset = LCD_OFFSET_LINE4

    self._send_byte(LCD_CMD_SET_DDRAM_ADDR | offset)

    for c in text[:20]:
      self._send_byte(ord(c), data=True)


  def clear(self):

    self._send_byte(LCD_CMD_CLEAR_DISPLAY, backlight=False)
