#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-26 tmp117_test.py

# tet for TMP117 driver


import os
import sys
import getopt
import signal

sys.path.append(os.path.join("..", "lib"))

import xmachine
import xtime
import sensors.tmp117


def _convert_validate(s, base, domain=None):

  tmp = 0

  try:
    tmp = int(s, base)
  except:
    return None

  if domain != None:
    if tmp not in domain:
      return None

  return tmp


if __name__ == "__main__":

  addr = 0x48

  iflag = False

  avalue = None
  cvalue = None

  bus = None

  xm = None
  xt = None
  s = None

  opts = None
  args = None

  # parse options

  try:
    opts, args = getopt.getopt(sys.argv[1:], "hia:c:B:", ["help", "id", "averaging=", "continuous=", "i2c_bus="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:
    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-i] [-c] [-a <average mode>] [-B <i2c bus>] [address]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-i" or o == "--id":
      iflag = True
    elif o == "-a" or o == "--averaging":
      avalue = _convert_validate(a, 10)
      if avalue == None:
        sys.stderr.write("Invalid averaging value.\n")
        sys.exit(2)
    elif o == "-c" or o == "--continuous":
      cvalue = _convert_validate(a, 10)
      if cvalue == None:
        sys.stderr.write("Invalid continuous interval value.\n")
        sys.exit(3)
    elif o == "-B" or o == "--i2c_bus":
      bus = _convert_validate(a, 10, range(0, 4 + 1))
      if bus == None:
        sys.stderr.write("Invalid I2C bus ID. Valid range is from 0 to 4\n")
        sys.exit(4)

  # were we given the device address?

  if len(args) > 0:

    addr = _convert_validate(args[0], 16, range(0x00, 0x7F + 1))

    if addr == None:
      sys.stderr.write("Invalid device address. Valid range is from 0x00 to 0x7F\n")
      sys.exit(5)

  # instantiate xtime object

  try:
    xt = xtime.XTime()
  except Exception as e:
    sys.stderr.write("Failed to instantiate XTime object: %s\n" % (e))
    sys.exit(6)

  # instantiate xmachine wrapper

  try:
    xm = xmachine.XMachine(bus)
  except Exception as e:
    sys.stderr.write("Failed to instantiate XMachine object: %s\n" % (e))
    sys.exit(7)

  # instantiate sensor object

  try:
    s = sensors.tmp117.TMP117(xm, xt, addr=addr)
  except Exception as e:
    sys.stderr.write("Failed to instantiate TMP117 object: %s\n" % (e))
    sys.exit(8)

  if iflag:

    # we just want the chip id

    cid = s.get_id()

    sys.stdout.write("%s (0x%02x, 0x%02x)\n" % (cid[2], cid[0], cid[1]))

  else:

    # validate avalue

    if avalue != None and avalue not in s.get_averaging():
      s.reset()
      sys.stderr.write("Invalid averaging value. Valid values are %s\n" % s.get_averaging())
      sys.exit(9)

    # validate cvalue

    if cvalue != None and cvalue not in s.get_intervals():
      s.reset()
      sys.stderr.write("Invalid inverval value. Valid values are %s\n" % s.get_intervals(avalue))
      sys.exit(10)

    # continuous?

    if cvalue != None and cvalue > 0:

      # setup sighandler

      quit = False

      def handler(sig, frame):
        global quit

        quit = True

      signal.signal(signal.SIGINT, handler)

      # configure

      s.set(avalue, cvalue)

      # start loop

      while not quit:

        sys.stdout.write("%8.3f C\n" % (s.get()))

    else:
    
      # one off measure
    
      s.set(avalue, 0)
    
      sys.stdout.write("%8.3f C\n" % (s.get()))

  # reset

  s.reset()

  sys.exit(0)
