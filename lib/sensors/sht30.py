#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-01-10 sht30.py

# SHT3x-DIS I2C driver
# Data from:
#  https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/2_Humidity_Sensors/Datasheets/Sensirion_Humidity_Sensors_SHT3x_Datasheet_digital.pdf


SHT30_CRC_POLY = 0x31
SHT30_CRC_INIT = 0xFF

# 16-bit commands for the different measure modes
#   single shot modes (0x00 and 0x01):
#     map[mode][repeatability] = command
#   periodic mode (0x02):
#     map[mode][repeatability][standby index] = command

SHT30_MODE_MAP = {
  0x00: {
    # single-shot, clock-stretch disabled
    0x00: [0x24, 0x16],
    0x01: [0x24, 0x0B],
    0x02: [0x24, 0x00]
  },
  0x01: {
    # single-shot, clock-stretch enabled
    0x00: [0x2C, 0x10],
    0x01: [0x2C, 0x0D],
    0x02: [0x2C, 0x06]
  },
  0x02: {
    # periodic/continuous
    # each contains another level of dict indexed by standby duration
    0x00 : {
      0x00: [0x27, 0x2A],
      0x01: [0x23, 0x29],
      0x02: [0x22, 0x2B],
      0x03: [0x21, 0x2D],
      0x04: [0x20, 0x2F]
    },
    0x01: {
      0x00: [0x27, 0x21],
      0x01: [0x23, 0x22],
      0x02: [0x22, 0x20],
      0x03: [0x21, 0x26],
      0x04: [0x20, 0x24]
    },
    0x02: {
      0x00: [0x27, 0x37],
      0x01: [0x23, 0x34],
      0x02: [0x22, 0x36],
      0x03: [0x21, 0x30],
      0x04: [0x20, 0x32]
    }
  }
}

# standby duration, in microseconds

SHT30_TSTANDBY_MAP = {
  0x00:  100000,
  0x01:  250000,
  0x02:  500000,
  0x03: 1000000,
  0x04: 2000000
}

# worst-case measurement duration, in microseconds, indexed by repeatability

SHT30_TMEASURE_MAP = {
  0x00:  4500,
  0x01:  6500,
  0x02: 15500
}


class SHT30:

  def __init__(self, xm, xt, addr=0x44):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._mode = 0x00
    self._repeatability = 0x00
    self._standby = 0x03

    self._time_ready = 0

    self.reset()


  def _crc(self, data):

    crc = SHT30_CRC_INIT

    for t in data:

      crc = crc ^ t

      for i in range(8):
        if crc & 0x80 == 0:
          crc = crc << 1
        else:
          crc = ((crc << 1) ^ SHT30_CRC_POLY) & 0xFF

    return crc


  def _validate(self, bdata1, bdata2, bcrc):

    return self._crc([bdata1, bdata2]) == bcrc


  def _calculate_h(self, bdata1, bdata2):

    return 100 * ((bdata1 << 8) | bdata2) / 65535.0


  def _calculate_t(self, bdata1, bdata2):

    return (175 * (((bdata1 << 8) | bdata2) / 65535.0)) - 45


  # mode:
  #  0x00 = single-shot, clock stretching disabled
  #  0x01 = single-shot, clock stretching enabled
  #  0x02 = continuous

  # repeatability:
  #   0x00 = low
  #   0x01 = medium
  #   0x02 = high

  # standby index (relevant only if mode == 0x02):
  #   0x00 =  100000 usecs, or 10.0 measurements per secs
  #   0x01 =  250000 usecs, or  4.0 measurements per secs
  #   0x02 =  500000 usecs, or  2.0 measurements per secs
  #   0x03 = 1000000 usecs, or  1.0 measurements per secs
  #   0x04 = 2000000 usecs, or  0.5 measurements per secs

  def _set(self, mode=None, repeatability=None, standby=None):

    cmd = [0x00, 0x00]

    if mode == None or mode not in SHT30_MODE_MAP.keys():
      self._mode = 0x00
    else:
      self._mode = mode

    if repeatability == None or repeatability not in SHT30_MODE_MAP[self._mode].keys():
      self._repeatability = 0x00
    else:
      self._repeatability = repeatability

    # for the two single-shot modes, map[mode][repeatability] contains the command
    # for continuous mode, there is another dict indexed by standby duration

    if self._mode != 0x02:
      cmd = SHT30_MODE_MAP[self._mode][self._repeatability]
    else:
      if standby == None or standby not in SHT30_TSTANDBY_MAP.keys():
        self._standby = 0x03
      else:
        self._standby = standby
      cmd = SHT30_MODE_MAP[self._mode][self._repeatability][self._standby]

    self._xm.i2c_write_bytes(self._addr, cmd)
    self._xt.sleep_us(1000)


  # send soft reset command

  def reset(self):

    # stop first

    self._xm.i2c_write_bytes(self._addr, [0x30, 0x93])
    self._xt.sleep_us(1000)

    # then reset

    self._xm.i2c_write_bytes(self._addr, [0x30, 0xA2])
    self._xt.sleep_us(1500)

    self._set()


  # repeatability:
  #   0x00 = low
  #   0x01 = medium
  #   0x02 = high
  # continuous:
  #         0 = single-shot mode
  #    100000 =  100 msecs, or 10.0 measurements per secs
  #    250000 =  250 msecs, or  4.0 measurements per secs
  #    500000 =  500 msecs, or  2.0 measurements per secs
  #   1000000 = 1000 msecs, or  1.0 measurements per secs
  #   2000000 = 2000 msecs, or  0.5 measurements per secs

  def set(self, repeatability=None, continuous=None):

    mode = self._mode
    standby = self._standby

    # if None or invalid, use current value

    if repeatability == None or repeatability not in SHT30_MODE_MAP[0x00].keys():
      repeatability = self._repeatability

    # were we asked to go in continuous mode?

    if continuous != None:

      if continuous == 0:

        mode = 0x00
        standby = 0x00

      elif continuous > 0 and continuous in SHT30_TSTANDBY_MAP.values():

        mode = 0x02
        standby = {y: x for x, y in SHT30_TSTANDBY_MAP.items()}[continuous]

        # absolute time until expiry

        self._time_ready = self._xt.time_us() + SHT30_TMEASURE_MAP[repeatability] + SHT30_TSTANDBY_MAP[standby]

    # always send stop command first

    self._xm.i2c_write_bytes(self._addr, [0x30, 0x93])
    self._xt.sleep_us(1000)

    # now set the mode

    self._set(mode, repeatability, standby)


  # returns a tuple: (relative humidity, temperature)

  def get(self):

    tmp_h = 0.00
    tmp_t = 0.00

    if self._mode == 0x02:

      # in continuous mode, block until the next cycle

      delta = self._time_ready - self._xt.time_us()

      if delta > 0:
        self._xt.sleep_us(delta)

      # write fetch command

      self._xm.i2c_write_bytes(self._addr, [0xE0, 0x00])
      self._xt.sleep_us(1000)

    else:

      # set single-shot mode

      self._set(self._mode, self._repeatability)

      # wait

      self._xt.sleep_us(SHT30_TMEASURE_MAP[self._repeatability])

    # now read 6 bytes: temp_byte1, temp_byte2, temp_crc, humi_byte1, humi_byte2, humi_crc

    data = self._xm.i2c_read_bytes(self._addr, 6)

    # validate and calculate

    if self._validate(data[3], data[4], data[5]):
      tmp_h = self._calculate_h(data[3], data[4])

    if self._validate(data[0], data[1], data[2]):
      tmp_t = self._calculate_t(data[0], data[1])

    # if in continuous mode, reset time to next cycle

    if self._mode == 0x02:

      self._time_ready = self._xt.time_us() + SHT30_TMEASURE_MAP[self._repeatability] + SHT30_TSTANDBY_MAP[self._standby]

    return (tmp_h, tmp_t)


  # returns list of valid invervals for use as value to the continuous parameter in set()

  def get_intervals(self):

    return sorted(SHT30_TSTANDBY_MAP.values())


  # returns list of valid values for the given mode for use as value to the repeatability parameter in set()
  #   0x00 = low
  #   0x01 = medium
  #   0x02 = high

  def get_repeatability(self, mode=None):

    if mode == None or mode not in SHT30_MODE_MAP.keys():
      mode = self._mode

    return sorted(SHT30_MODE_MAP[mode].keys())
