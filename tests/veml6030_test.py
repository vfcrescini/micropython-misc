#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-30 veml6030_test.py

# test for VEM6030 driver

import os
import sys
import getopt
import signal

sys.path.append(os.path.join("..", "lib"))

import xmachine
import xtime
import sensors.veml6030


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

  import getopt
  import signal

  addr = 0x10

  gvalue = None
  ivalue = None
  pvalue = None
  cvalue = None

  bus = None

  xm = None
  xt = None
  s = None

  opts = None
  args = None

  # parse options

  try:
    opts, args = getopt.getopt(sys.argv[1:], "hg:i:p:cB:", ["help", "gain=", "inttime=", "powersave=", "continuous", "i2c_bus="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:
    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-g <gain>] [-i <integration time>] [-p <powersave mode>] [-c] [-B <i2c bus>] [address]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-g" or o == "--gain":
      gvalue = _convert_validate(a, 10)
      if gvalue == None:
        sys.stderr.write("Invalid gain value\n")
        sys.exit(2)
    elif o == "-i" or o == "--inttime":
      ivalue = _convert_validate(a, 10)
      if ivalue == None:
        sys.stderr.write("Invalid integration time value\n")
        sys.exit(3)
    elif o == "-p" or o == "--powersave":
      pvalue = _convert_validate(a, 10)
      if pvalue == None:
        sys.stderr.write("Invalid power save value\n")
        sys.exit(4)
    elif o == "-c" or o == "--continuous":
      cvalue = True
    elif o == "-B" or o == "--i2c_bus":
      bus = _convert_validate(a, 10, range(0, 4 + 1))
      if bus == None:
        sys.stderr.write("Invalid I2C bus ID. Valid range is from 0 to 4\n")
        sys.exit(5)


  # were we given the device address?

  if len(args) > 0:

    addr = _convert_validate(args[0], 16, range(0x00, 0x7F + 1))

    if addr == None:
      sys.stderr.write("Invalid device address. Valid range is from 0x00 to 0x7F\n")
      sys.exit(6)

  # instantiate xtime object

  try:
    xt = xtime.XTime()
  except Exception as e:
    sys.stderr.write("Failed to instantiate XTime object: %s\n" % (e))
    sys.exit(7)

  # instantiate xmachine wrapper

  try:
    xm = xmachine.XMachine(bus)
  except Exception as e:
    sys.stderr.write("Failed to instantiate XMachine object: %s\n" % (e))
    sys.exit(8)

  # instantiate sensor object

  try:
    s = sensors.veml6030.VEML6030(xm, xt, addr=addr)
  except Exception as e:
    sys.stderr.write("Failed to instantiate VEML6030 object: %s\n" % (e))
    sys.exit(9)

  # validate gvalue

  if gvalue != None and gvalue not in s.get_gain():
    s.reset()
    sys.stderr.write("Invalid gain value. Valid values are %s\n" % s.get_gain())
    sys.exit(10)

  # validate ivalue

  if ivalue != None and ivalue not in s.get_inttime():
    s.reset()
    sys.stderr.write("Invalid integration time value. Valid values are %s\n" % s.get_inttime())
    sys.exit(11)

  # validate pvalue

  if pvalue != None and pvalue not in s.get_psmode():
    s.reset()
    sys.stderr.write("Invalid powersave mode values. Valid values are %s\n" % s.get_psmode())
    sys.exit(12)

  # continuous?

  if cvalue:

    # setup sighandler

    quit = False

    def handler(sig, frame):
      global quit

      quit = True

    signal.signal(signal.SIGINT, handler)

    # configure

    s.set(gain=gvalue, inttime=ivalue, powersave=pvalue, continuous=True)

    # start loop

    while not quit:

      sys.stdout.write("%8.3f lux\n" % (s.get()[0]))

  else:

    # one off measure

    s.set(gain=gvalue, inttime=ivalue, powersave=pvalue, continuous=False)

    sys.stdout.write("%9.3f lux\n" % (s.get()[0]))

  # reset

  s.reset()

  sys.exit(0)
