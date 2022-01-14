#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-09 hd44780_test.py

# test for HD44870 driver

import os
import sys
import getopt
import signal

sys.path.append(os.path.join("..", "lib"))

import xmachine
import xtime
import displays.hd44780


def _shex2int(shex, vmin, vmax):

  tmp = 0

  try:
    tmp = int(shex, 16)
  except:
    return None

  if tmp < vmin or tmp > vmax:
    return None

  return tmp


if __name__ == "__main__":

  addr = 0x27

  bus = None

  cflag = False

  text = []

  # parse options

  try:
    opts, args = getopt.getopt(sys.argv[1:], "hct:B:", ["help", "clear", "text=", "i2c_bus="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:
    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-c] [-t text line 1 [-t text line 2 [...]]] [-B <i2c bus>] [address]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-c" or o == "--clear":
      cflag = True
    elif o == "-t" or o == "--text":
      if len(text) == 4:
        sys.stderr.write("Ignoring fifth and subsequent lines\n")
      else:
        text.append(a[:20])
    elif o == "-B" or o == "--i2c_bus":
      bus = _shex2int(a, 0x00, 0x04)
      if bus == None:
        sys.stderr.write("Invalid I2C bus ID. Valid range is from 0x00 to 0x04\n")
        sys.exit(1)

  # were we given the device address?

  if len(args) > 0:

    addr = _shex2int(args[0], 0x00, 0x7F)

    if addr == None:
      sys.stderr.write("Invalid device address. Valid range is from 0x00 to 0x7F\n")
      sys.exit(2)

  # was there actually anything for us to do?

  if cflag or len(text) > 0:

    xm = None
    xt = None
    dsp = None

    try:
      xt = xtime.XTime()
    except Exception as e:
      sys.stderr.write("Failed to instantiate XTime object: %s\n" % (e))
      sys.exit(3)

    # instantiate xmachine wrapper
  
    try:
      xm = xmachine.XMachine(bus)
    except Exception as e:
      sys.stderr.write("Failed to instantiate XMachine object: %s\n" % (e))
      sys.exit(4)
  
    # instantiate display object
  
    try:
      dsp = displays.hd44780.HD44780(xm, xt, addr=addr)
    except Exception as e:
      sys.stderr.write("Failed to instantiate HD44780 object: %s\n" % (e))
      sys.exit(5)

    # display

    for i, line in enumerate(text):
      dsp.show(line, i + 1)

    # clear

    if cflag:
      dsp.clear()

  sys.exit(0)
