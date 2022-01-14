#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-26 tmp117.py

# TMP117 I2C driver
# Data from:
#   https://www.ti.com/lit/gpn/tmp117


import struct


# chip IDs mapped to chip descriptions

TMP117_ID_MAP = {
  0x117: "TMP117"
}

# averaging modes
# values are the number of conversions/measures to be taken

TMP117_AVERAGING_MAP = {
  0x00:  0,
  0x01:  8,
  0x02: 32,
  0x03: 64
}

# conversion cycle time in microseconds, which is the sum of active conversion
# time (measure duration) and standby duration
#   map[conv index][averging index] = microseconds

TMP117_TCONVERSION_MAP = {
  0x00: {
    0x00:    15500,
    0x01:   125000,
    0x02:   500000,
    0x03:  1000000
  },
  0x01: {
    0x00:   125000,
    0x01:   125000,
    0x02:   500000,
    0x03:  1000000
  },
  0x02: {
    0x00:   250000,
    0x01:   250000,
    0x02:   500000,
    0x03:  1000000
  },
  0x03: {
    0x00:   500000,
    0x01:   500000,
    0x02:   500000,
    0x03:  1000000
  },
  0x04: {
    0x00:  1000000,
    0x01:  1000000,
    0x02:  1000000,
    0x03:  1000000
  },
  0x05: {
    0x00:  4000000,
    0x01:  4000000,
    0x02:  4000000,
    0x03:  4000000
  },
  0x06: {
    0x00:  8000000,
    0x01:  8000000,
    0x02:  8000000,
    0x03:  8000000
  },
  0x07: {
    0x00: 16000000,
    0x01: 16000000,
    0x02: 16000000,
    0x03: 16000000
  }
}


class TMP117:

  def __init__(self, xm, xt, addr=0x48):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._chip_id = 0x00
    self._rev_num = 0x00

    self._mode = 0x01
    self._averaging = 0x00
    self._conversion = 0x00

    self._time_ready = 0

    self.reset()

    self._get_data_rom()


  def _get_data_rom(self):

    # get chip id at 0x0F

    d = struct.unpack(">H", bytes(self._xm.i2c_read(self._addr, 0x0F, 2)))[0]

    self._chip_id = d & 0x1FFF
    self._rev_num = (d & 0xE000) >> 13


  def _get_data_sensor(self):

    data = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x00, 2)))[0]

    return data / 128.0


  # returns tuple of booleans: (chip-ready, data-ready)

  def _get_status(self):

    # eeprom busy is thirteenth bit
    # data ready is fourteenth bit

    status = struct.unpack(">H", bytes(self._xm.i2c_read(self._addr, 0x01, 2)))[0]

    return (((status & 0x1000) >> 12) == 0x00, ((status & 0x2000) >> 13) == 0x01)


  # mode:
  #   0x00 = continuous
  #   0x01 = shutdown
  #   0x02 = continuous (same as 0x00)
  #   0x03 = one-shot

  # averaging:
  #   0x00 = no averaging
  #   0x01 =  8 averaged conversions
  #   0x02 = 32 averaged conversions
  #   0x03 = 64 averaged conversions

  # conversion:
  #   0x00 to 0x07; see TMP117_TCONVERSION_MAP

  def _set(self, mode=None, averaging=None, conversion=None):

    if mode == None or mode not in range(0, 0x04):
      self._mode = 0x01
    else:
      self._mode = mode

    if averaging == None or averaging not in TMP117_AVERAGING_MAP.keys():
      self._averaging = 0x00
    else:
      self._averaging = averaging

    if conversion == None or conversion not in TMP117_TCONVERSION_MAP.keys():
      self._conversion = 0x00
    else:
      self._conversion = conversion

    tmp = 0x00
    tmp = tmp | ((self._mode & 0x03) << 10)
    tmp = tmp | ((self._averaging & 0x03) << 5)
    tmp = tmp | ((self._conversion & 0x07) << 7)

    self._xm.i2c_write(self._addr, 0x01, [tmp & 0x00ff, (tmp & 0xff00) >> 8])


  # send reset command; block until ready

  def reset(self):

    # reset + shutdown
    # reset flag is second bit
    # shutdown mode is 0 (tenth bit) and 1 (eleventh bit)

    self._xm.i2c_write(self._addr, 0x01, [0x02, 0x04])

    # sleep until ready

    while not self._get_status()[0]:
      self._xt.sleep_ms(1)

    self._set()


  # set sensor mode

  #   averaging:
  #     0x00: no averaging
  #     0x01:  8 averaged conversions
  #     0x02: 32 averaged conversions
  #     0x03: 64 averaged conversions

  #   continuous:
  #           0 = single-shot mode
  #       15500 =    15.5 msecs
  #      125000 =   125.0 msecs
  #      250000 =   250.0 msecs
  #      500000 =   500.0 msecs
  #     1000000 =  1000.0 msecs
  #     4000000 =  4000.0 msecs
  #     8000000 =  8000.0 msecs
  #    16000000 = 16000.0 msecs

  def set(self, averaging=None, continuous=None):

    mode = self._mode
    aindex = self._averaging
    cindex = self._conversion

    # always set shutdown mode first

    self._set(mode=0x01)

    # build temporary reverse dict to find the correct index from given value

    amap = {y: x for x, y in TMP117_AVERAGING_MAP.items()}

    if averaging != None and averaging in amap:
      aindex = amap[averaging]

    # build temporary reverse dict to find the correct index from given value and averaging

    cmap = {y[aindex] : x for x, y in TMP117_TCONVERSION_MAP.items()}
      
    if continuous != None and continuous > 0 and continuous in cmap:
      mode = 0x00
      cindex = cmap[continuous]

      # absolute time until expiry

      self._time_ready = self._xt.time_us() + TMP117_TCONVERSION_MAP[cindex][aindex]

    # set mode

    self._set(mode=mode, averaging=aindex, conversion=cindex)


  # returns temperature in C

  def get(self):

    if self._mode == 0x00 or self._mode == 0x10:

      # in continuous mode, block until the next cycle

      delta = self._time_ready - self._xt.time_us()

      if delta > 0:
        self._xt.sleep_us(delta)

    else:

      # if we're in anything other than continuous mode

      # set one-shot mode

      self._set(mode=0x03, averaging=self._averaging, conversion=0x00)

      # mandatory wait

      self._xt.sleep_us(15500)

    # make sure we're ready to read

    while not self._get_status()[1]:
      self._xt.sleep_ms(1)

    # read data

    data = self._get_data_sensor()

    # in continuous mode, reset time to next cycle

    if self._mode == 0x00 or self._mode == 0x10:
      self._time_ready = self._xt.time_us() + TMP117_TCONVERSION_MAP[self._conversion][self._averaging]

    return data


  def get_id(self):

    chip_desc = "Unknown"

    if self._chip_id in TMP117_ID_MAP.keys():
      chip_desc = "%s (rev %d)" % (TMP117_ID_MAP[self._chip_id], self._rev_num)

    return (self._chip_id, self._rev_num, chip_desc)


  # returns list of invervals valid for the given averaging setting for use
  # as value to the continuous parameter in set()

  def get_intervals(self, averaging=None):

    amap = {y: x for x, y in TMP117_AVERAGING_MAP.items()}
    aindex = self._averaging

    if averaging != None and averaging in amap.keys():
      aindex = amap[averaging]

    return sorted(set([x[aindex] for x in TMP117_TCONVERSION_MAP.values()]))


  # returns list of valid averaging values for use as parameter in set()

  def get_averaging(self):

    return sorted(TMP117_AVERAGING_MAP.values())
