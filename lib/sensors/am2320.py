#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-01-15 am2320.py

# AM2320 I2C driver
# Data from:
#   https://cdn-shop.adafruit.com/product-files/3721/AM2320.pdf


import struct


# standby duration, in microseconds

AM2320_TSTANDBY_MAP = {
  0x00:        0,
  0x01:   250000,
  0x02:   500000,
  0x03:  1000000,
  0x04:  2000000,
  0x05:  4000000,
  0x06:  8000000
}


class AM2320:

  def __init__(self, xm, xt, addr=0x5C):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._standby = 0x00

    self._time_ready = 0


  def _crc(self, data):

    crc = 0xFFFF

    for t in data:

      crc = crc ^ t

      for i in range(8):
        if crc & 0x01 == 1:
          crc = (crc >> 1) ^ 0xA001
        else:
          crc = crc >> 1

    return crc


  def _validate(self, data, crc):

    return self._crc(data) == struct.unpack('<H', bytearray(crc))[0]


  def _calculate_h(self, data):

    return struct.unpack('>h', bytearray(data))[0] / 10.0


  def _calculate_t(self, data):

    return struct.unpack('>H', bytearray(data))[0] / 10.0


  # the chip doesn't support soft-reset
  # all this does is reset the object state

  def reset(self):

    self._standby = 0x00
    self._time_ready = 0


  # continuous:
  #         0 = single-shot mode
  #    250000 =  250 msecs
  #    500000 =  500 msecs
  #   1000000 = 1000 msecs
  #   2000000 = 2000 msecs
  #   4000000 = 4000 msecs
  #   8000000 = 8000 msecs

  def set(self, continuous=None):

    # were we asked to go in continuous mode?

    if continuous != None:

      if continuous == 0:

        self._standby = 0

      elif continuous > 0 and continuous in AM2320_TSTANDBY_MAP.values():

        self._standby = {y: x for x, y in AM2320_TSTANDBY_MAP.items()}[continuous]

        #  absolute time until expiry

        self._time_ready = self._xt.time_us() + AM2320_TSTANDBY_MAP[self._standby]


  # returns a tuple: (relative humidity, temperature)

  def get(self):

    tmp_h = 0.00
    tmp_t = 0.00

    if self._standby > 0x00:

      # in continuous mode, block until the next cycle

      delta = self._time_ready - self._xt.time_us()

      if delta > 0:
        self._xt.sleep_us(delta)

    # send null command to wake up sensor

    try:
      self._xm.i2c_write_byte(self._addr, 0x00)
    except:
      pass

    self._xt.sleep_us(1000)

    # now send command to read the two x two-byte registers containing the data

    self._xm.i2c_write_bytes(self._addr, [0x03, 0x00, 0x04])

    self._xt.sleep_us(2000)

    # read the two x two-byte register data + another two bytes containing CRC

    data = self._xm.i2c_read_bytes(self._addr, 8)

    # validate and calculate

    if self._validate(data[0:6], data[6:8]):
      tmp_h = self._calculate_h(data[2:4])
      tmp_t = self._calculate_t(data[4:6])

    # if in continuous mode, reset time to next cycle

    if self._standby > 0x00:

      self._time_ready = self._xt.time_us() + AM2320_TSTANDBY_MAP[self._standby]

    return (tmp_h, tmp_t)


  # returns list of valid invervals for use as value to the continuous parameter in set()

  def get_intervals(self):

    return sorted(AM2320_TSTANDBY_MAP.values())
