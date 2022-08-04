#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-08-04 mpu6050_test.py

# test for MPU6050 driver


import os
import sys
import getopt
import signal

sys.path.append(os.path.join("..", "lib"))

import xmachine
import xtime
import sensors.mpu6050


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

  addr = 0x68

  avalue = None
  gvalue = None
  cvalue = None

  bus = None

  xm = None
  xt = None
  s = None

  opts = None
  args = None

  # parse options

  try:
    opts, args = getopt.getopt(sys.argv[1:], "ha:g:c:B:", ["help", "asensitivity=", "gsensitivity=", "continuous=", "i2c_bus="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:
    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-i] [-a <accel sesitivity>] [-g <gyro sensitivity>] [-c <interval>] [-B <i2c bus>] [address]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-a" or o == "--asensitivity":
      avalue = _convert_validate(a, 10)
      if avalue == None:
        sys.stderr.write("Invalid accelerometer sensitivity value.\n")
        sys.exit(2)
    elif o == "-g" or o == "--gsensitivity":
      gvalue = _convert_validate(a, 10)
      if gvalue == None:
        sys.stderr.write("Invalid gyroscope sensitivity value.\n")
        sys.exit(3)
    elif o == "-c" or o == "--continuous":
      cvalue = _convert_validate(a, 10)
      if cvalue == None:
        sys.stderr.write("Invalid continuous interval value.\n")
        sys.exit(4)
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
    s = sensors.mpu6050.MPU6050(xm, xt, addr=addr)
  except Exception as e:
    sys.stderr.write("Failed to instantiate MPU6050 object: %s\n" % (e))
    sys.exit(9)

  # validate avalue

  if avalue != None and avalue not in sensors.mpu6050.MPU6050_RANGEA_MAP.values():
    sys.stderr.write("Invalid accelerometer sensitivity value. Valid values are %s\n" % sensors.mpu6050.MPU6050_RANGEA_MAP.values())
    sys.exit(10)

  # validate cvalue

  if gvalue != None and gvalue not in sensors.mpu6050.MPU6050_RANGEG_MAP.values():
    sys.stderr.write("Invalid gyroscope sensitivity value. Valid values are %s\n" % sensors.mpu6050.MPU6050_RANGEG_MAP.values())
    sys.exit(11)

  # continuous?

  if cvalue != None and cvalue > 0:

    # setup sighandler

    quit = False

    def handler(sig, frame):
      global quit

      quit = True

    signal.signal(signal.SIGINT, handler)

    # configure

    s.set(avalue, gvalue)

    # start loop

    while not quit:

      sys.stdout.write("%8.3f, %8.3f, %8.3f, %8.3f, %8.3f, %8.3f, %8.3f\n" % (s.get()))
      xt.sleep_ms(cvalue)

  else:
  
    # one off measure
  
    sys.stdout.write("%8.3f, %8.3f, %8.3f, %8.3f, %8.3f, %8.3f, %8.3f\n" % (s.get()))

  # reset

  s.reset()

  sys.exit(0)
