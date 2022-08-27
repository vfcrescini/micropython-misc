#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-14 clock_sensor_rpi.py

# clock weather sensor webserver for Raspberry PI


import os
import sys
import getopt
import signal

sys.path.append(os.path.join("..", "..", "lib"))

import xmachine
import xtime
import displays.hd44780
import sensors.bme280


stop = False


def _handler(sig, _):

  global stop

  stop = True


def _str2int(s, base, vmin, vmax):

  tmp = 0

  try:
    tmp = int(s, base)
  except:
    return None

  if tmp < vmin or tmp > vmax:
    return None

  return tmp


if __name__ == "__main__":

  fflag = False
  pint = 5

  daddr = 0x27
  saddr = 0x76

  bus = None

  xm = None
  xt = None
  ddev = None
  sdev = None

  # parse options

  opts = None
  args = None

  try:
    opts, args = getopt.getopt(sys.argv[1:], "h4i:B:d:s:", ["help", "four", "probe_interval=", "i2c_bus=", "addr_display=", "addr_seonsor="])
  except Exception as e:
    sys.stderr.write("Failed to parse arguments: %s\n" % (e))
    sys.exit(1)

  for o, a in opts:

    if o == "-h" or o == "--help":
      sys.stdout.write("Usage: %s [-h] [-4] [-i <probe interval>] [-B <i2c bus>] [-d <display address>] [-s <sensor address>]\n" % (sys.argv[0]))
      sys.exit(0)
    elif o == "-4" or o == "--four":
      fflag = True 
    elif o == "-i" or o == "--probe_interval":
      pint = __str2int(a, 10, 1, 300)
      if pint == None:
        sys.stderr.write("Invalid probe interval. Valid range is from 1 secs to 300 secs (5 minutes)\n")
        sys.exit(2)
    elif o == "-B" or o == "--i2c_bus":
      bus = _str2int(a, 16, 0x00, 0x04)
      if bus == None:
        sys.stderr.write("Invalid I2C bus ID. Valid range is from 0x00 to 0x04\n")
        sys.exit(3)
    elif o == "-d" or o == "--addr_display":
      daddr = _str2int(a, 16, 0x00, 0x7F)
      if daddr == None:
        sys.stderr.write("Invalid display address. Valid range is from 0x00 to 0x7F\n")
        sys.exit(4)
    elif o == "-s" or o == "--addr_sensor":
      saddr = _str2int(a, 16, 0x00, 0x7F)
      if saddr == None:
        sys.stderr.write("Invalid sensor address. Valid range is from 0x00 to 0x7F\n")
        sys.exit(5)

  # instantiate xtime wrapper

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

  # init display and sensor

  try:
    ddev = displays.hd44780.HD44780(xm, xt, addr=daddr)
  except Exception as e:
    sys.stderr.write("Failed to instantiate display object: %s\n" % (e))
    sys.exit(8)

  try:
    sdev = sensors.bme280.BME280(xm, xt, addr=saddr)
  except Exception as e:
    sys.stderr.write("Failed to instantiate sensor object: %s\n" % (e))
    sys.exit(9)

  signal.signal(signal.SIGINT, _handler)

  # init display buffer

  linebuf_cur = [""] * (4 if fflag else 2)
  linebuf_new = [""] * (4 if fflag else 2)

  # init other stuff that we need in the main loop

  psec = pint
  humi = 0.0
  temp = 0.0
  pres = 0.0

  # align loop to the nearest clock second

  xt.sleep_ms(1000 - (xt.time_ms() % 1000))

  while not stop:

    t_start = xt.time_ms()

    # compose strings

    lt = xt.localtime(t_start // 1000)

    if fflag:

      linebuf_new[0] = "%02d/%02d/%04d  %02d:%02d:%02d" % (lt[2], lt[1], lt[0], lt[3], lt[4], lt[5])
      linebuf_new[1] = "Humidity:     %5.1f%%" % (humi)
      linebuf_new[2] = "Temperature: %6.1fC" % (temp)
      linebuf_new[3] = "Pressure:  %6.1fhPa" % (pres)

    else:

      linebuf_new[0] = "%02d/%02d   %02d:%02d:%02d" % (lt[2], lt[1], lt[3], lt[4], lt[5])
      linebuf_new[1] = "% 5.1fC %6.1fhPa" % (temp, pres)

    # update line 1 only if there is a change

    if linebuf_cur[0] != linebuf_new[0]:
      linebuf_cur[0] = linebuf_new[0]
      ddev.show(linebuf_cur[0], 1)

    # update line 2 only if there is a change

    if linebuf_cur[1] != linebuf_new[1]:
      linebuf_cur[1] = linebuf_new[1]
      ddev.show(linebuf_cur[1], 2)

    # update line 3 only if there is a change

    if fflag and linebuf_cur[2] != linebuf_new[2]:
      linebuf_cur[2] = linebuf_new[2]
      ddev.show(linebuf_cur[2], 3)

    # update line 4 only if there is a change

    if fflag and linebuf_cur[3] != linebuf_new[3]:
      linebuf_cur[3] = linebuf_new[3]
      ddev.show(linebuf_cur[3], 4)

    # probe sensor at the specified interval

    if psec >= pint:

      psec = 0
      humi, temp, pres = sdev.get()

    else:

      psec = psec + 1

    # if everything we've done so far was done in under 1 second, sleep until the next second

    t_end = xt.time_ms()

    if (t_end - t_start) < 1000:
      xt.sleep_ms(1000 - (t_end % 1000))

  sdev.reset()
  ddev.clear()

  sys.exit(0)
