#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-30 veml6030.py

# VEML6030 I2C driver
# Data from:
#  https://www.vishay.com/docs/84366/veml6030.pdf


import struct


# gain factor indexes -- really odd that these are not in order
# factors are x 1000 to avoid floats

VEML6030_GAIN_MAP = {
  0x00: 1000,
  0x01: 2000,
  0x02:  125,
  0x03:   25
}

# integration time in microsecs -- again, not in order, and with missing entries

VEML6030_INTTIME_MAP = {
  0x00: 100000,
  0x01: 200000,
  0x02: 400000,
  0x03: 800000,
  0x08:  50000,
  0x0C:  25000,
}

# power mode time in microsecs

VEML6030_PSAVETIME_MAP = {
  0x00:  500000,
  0x01: 1000000,
  0x02: 2000000,
  0x03: 4000000,
}

# The table from the datasheet is incomplete; it only shows rows where gain == 2. Assuming that the
# gain value is a power-of-two multiplier, we can extrapolate the missing rows by doulbling or halving
# known rows.
# dict is [gain][integration_time] = resolution

VEML6030_RESOLUTION_MAP = {
  0x00: {
    0x00: 0.0576,
    0x01: 0.0288,
    0x02: 0.0144,
    0x03: 0.0072,
    0x08: 0.1152,
    0x0C: 0.2304,
  },
  0x01: {
    0x00: 0.0288,
    0x01: 0.0144,
    0x02: 0.0072,
    0x03: 0.0036,
    0x08: 0.0576,
    0x0C: 0.1152
  },
  0x02: {
    0x00: 0.4608,
    0x01: 0.2304,
    0x02: 0.1152,
    0x03: 0.0576,
    0x08: 0.9216,
    0x0C: 1.8432 
  },
  0x03: {
    0x00: 0.2304,
    0x01: 0.1152,
    0x02: 0.0576,
    0x03: 0.0288,
    0x08: 0.4608,
    0x0C: 0.9216
  }
}


class VEML6030:

  def __init__(self, xm, xt, addr=0x10):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._gain = 0x00
    self._inttime = 0x00
    self._power = 0x00
    self._psenable = 0x00
    self._psmode = 0x0

    self._time_ready = 0
    self._continuous = False

    self.reset()


  def _get_data_sensor(self):

    # get raw data
    # datasheet says MSB goes to the higher addresses, so these 2-byte registers are little endian

    als = struct.unpack("<H", bytes(self._xm.i2c_read(self._addr, 0x04, 2)))[0]
    white = struct.unpack("<H", bytes(self._xm.i2c_read(self._addr, 0x05, 2)))[0]
   
    # get resolution (lux/bit)

    resolution = VEML6030_RESOLUTION_MAP[self._gain][self._inttime]

    return als * resolution, white * resolution


  # gain:
  #   0x00 = 1000
  #   0x01 = 2000
  #   0x02 =  125
  #   0x03 =   25

  # inttime:
  #   0x00 = 100
  #   0x01 = 200
  #   0x02 = 400
  #   0x03 = 800
  #   0x08 =  50
  #   0x0C =  25

  # power:
  #   0x00 = on
  #   0x01 = off

  def _set_mode(self, gain=None, inttime=None, power=None):

    if gain == None or gain not in VEML6030_GAIN_MAP.keys():
      self._gain = 0x02
    else:
      self._gain = gain

    if inttime == None or inttime not in VEML6030_INTTIME_MAP.keys():
      self._inttime = 0x00
    else:
      self._inttime = inttime

    if power == None or power not in [0x00, 0x01]:
      self._power = 0x01
    else:
      self._power = power

    # register   0000 0000 0000 0000
    # gain       0001 1000 0000 0000
    # int time   0000 0011 1100 0000
    # power      0000 0000 0000 0001

    tmp = ((self._gain & 0x03) << 11) | ((self._inttime & 0x0f) << 6) | (self._power & 0x01)

    self._xm.i2c_write(self._addr, 0x00, [tmp & 0x00ff, (tmp & 0xff00) >> 8])


  # psenable:
  #   0x00 = disabled
  #   0x01 = enabled

  # psmode:
  #   0x00 = mode 1
  #   0x01 = mode 2
  #   0x02 = mode 3
  #   0x03 = mode 4

  def _set_powersave(self, psenable=None, psmode=None):

    if psenable == None or psenable not in [0x00, 0x01]:
      self._psenable = 0x00
    else:
      self._psenable = psenable

    if psmode == None or psmode not in VEML6030_PSAVETIME_MAP.keys():
      self._psode = 0x00
    else:
      self._psmode = psmode

    # register   0000 0000 0000 0000
    # psenable   0000 0000 0000 0001
    # psmode     0000 0000 0000 0110

    tmp = ((self._psmode & 0x11) << 1) | (self._psenable & 0x01)

    self._xm.i2c_write(self._addr, 0x03, [tmp & 0x00ff, 0x00])


  # interval between measurements in microseconds
  # the return value of this function should reflect the values in the "Refresh
  # Time" column of the "Refresh time, IDD and Resolution Relation" table in
  # the datasheet

  def _get_tstandby(self):

    tmp = 0

    # add integration time

    tmp = tmp + VEML6030_INTTIME_MAP[self._inttime]

    # add power saving mode time

    if self._psenable:
      tmp = tmp + VEML6030_PSAVETIME_MAP[self._psmode]
    
    return tmp


  # there is no reset command; just shutdown

  def reset(self):

    self._set_mode()
    self._set_powersave()


  # gain (fain factor scaled x 1000):
  #     25 = x 0.25
  #    125 = x 0.125
  #   1000 = x 1.0
  #   2000 = x 2.0

  # inttime (integration time in usecs):
  #    25000 =  25 msecs
  #    50000 =  50 msecs
  #   100000 = 100 msecs
  #   200000 = 200 msecs
  #   400000 = 400 msecs
  #   800000 = 800 msecs

  # powersave (this is NOT the same as psmode):
  #   0x00 = off
  #   0x01 = mode 1
  #   0x02 = mode 2
  #   0x03 = mode 3
  #   0x04 = mode 4

  # continuous -- only on or off; actual duration is defined by inttime and powersave
  #  False = off
  #  True  = on

  def set(self, gain=None, inttime=None, powersave=None, continuous=None):

    # gain

    gindex = self._gain
    gmap = {y: x for x, y in VEML6030_GAIN_MAP.items()}

    if gain != None and gain in gmap:
      gindex = gmap[gain]

    # inttime

    iindex = self._inttime
    imap = {y: x for x, y in VEML6030_INTTIME_MAP.items()}

    if inttime != None and inttime in imap:
      iindex = imap[inttime]

    # powersave

    psenable = self._psenable
    psmode = self._psmode

    if powersave != None:
      if powersave == 0:
        psenable = 0x00
        psmode = 0x00
      elif powersave > 0 and powersave <= 4:
        psenable = 0x01
        psmode = powersave - 1

    # continuous

    if continuous != None and isinstance(continuous, bool):
      self._continuous = continuous

    # set powersave now, before the mode

    self._set_powersave(psenable=psenable, psmode=psmode)

    # were we asked to go in continuous mode?

    if self._continuous:

      # turn on power in continuous mode

      self._set_mode(gain=gain, inttime=inttime, power=0x00)

      # absolute time until ready, in microsecs
      # first reading after powerup is garbage, so sleep twice as long to get the second reading

      self._time_ready = self._xt.time_us() + (self._get_tstandby() * 2)

    else:

      # in one-shot mode, shutdown

      self._set_mode(gain=gain, inttime=inttime, power=0x01)


  # returns tuple: resolution lux/bit, white lux/bit

  def get(self):

    sleep = 0

    if self._continuous:

      # continuous

      # how long till ready?

      sleep = self._time_ready - self._xt.time_us()

    else:

      # one-shot

      # turn on

      self._set_mode(gain=self._gain, inttime=self._inttime, power=0x00)

      # how long till ready?
      # first reading after powerup is garbage, so sleep twice as long to get the second reading

      sleep = self._get_tstandby() * 2

    # sleep until ready

    if sleep > 0:
      self._xt.sleep_us(sleep)

    # read data

    data = self._get_data_sensor()

    if self._continuous:

      # in continuous mode, reset time to next cycle

      self._time_ready = self._xt.time_us() + self._get_tstandby()

    else:

      # in one-shot mode, shutdown

      self._set_mode(gain=self._gain, inttime=self._inttime, power=0x01)

    return data


  # returns a list of valid gain values for use as parameter in set()

  def get_gain(self):

    return sorted(VEML6030_GAIN_MAP.values())


  # returns a list of valid integration time values for use as parameter is set()

  def get_inttime(self):

    return sorted(VEML6030_INTTIME_MAP.values())


  # returns a list of valid powersave values for use as parameter is set()

  def get_psmode(self):

    return list(range(5))
