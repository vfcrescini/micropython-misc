#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-10-30 bme280.py

# BME280 I2C driver 
# Data from:
#   https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf


import struct

# BME280 standby duration indices; duration in microseconds

BME280_TSTANDBY_MAP = {
  0x00:     500,
  0x01:   62500,
  0x02:  125000,
  0x03:  250000,
  0x04:  500000,
  0x05: 1000000,
  0x06:   10000,
  0x07:   20000
}

# BMP280 standby duration indices; duration in microseconds

BME280_TSTANDBY2_MAP = {
  0x00:     500,
  0x01:   62500,
  0x02:  125000,
  0x03:  250000,
  0x04:  500000,
  0x05: 1000000,
  0x06: 2000000,
  0x07: 4000000
}

# oversampling; zero means disabled

BME280_OVERSAMPLING_MAP = {
  0x00:  0,
  0x01:  1,
  0x02:  2,
  0x03:  4,
  0x04:  8,
  0x05: 16
}

# chip IDs mapped to chip descriptions

BME280_ID_MAP = {
  0x56: "BMP280 (sample)",
  0x57: "BMP280 (sample)",
  0x58: "BMP280",
  0x60: "BME280"
}


class BME280:

  def __init__(self, xm, xt, addr=0x77):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._chip_id = 0x00

    self._mode_h = 0x00
    self._mode_t = 0x00
    self._mode_p = 0x00
    self._mode = 0x00

    self._standby = 0x05

    self._trim_t1 = 0x00
    self._trim_t2 = 0x00
    self._trim_t3 = 0x00
    self._trim_p1 = 0x00
    self._trim_p2 = 0x00
    self._trim_p3 = 0x00
    self._trim_p4 = 0x00
    self._trim_p5 = 0x00
    self._trim_p6 = 0x00
    self._trim_p7 = 0x00
    self._trim_p8 = 0x00
    self._trim_p9 = 0x00
    self._trim_h1 = 0x00
    self._trim_h2 = 0x00
    self._trim_h3 = 0x00
    self._trim_h4 = 0x00
    self._trim_h5 = 0x00
    self._trim_h6 = 0x00

    self._time_ready = 0

    self.reset()


  def _get_data_rom(self):

    # get chip id at 0xD0

    self._chip_id = self._xm.i2c_read(self._addr, 0xD0, 1)[0]

    # get trim parameters

    data = self._xm.i2c_read(self._addr, 0x88, 26) + self._xm.i2c_read(self._addr, 0xE0, 8)

    # data[0]  : 0x88
    # ...
    # data[25] : 0xA1
    # data[26] : 0xE0
    # data[27] : 0xE1
    # data[28] : 0xE2
    # data[29] : 0xE3
    # data[30] : 0xE4
    # data[31] : 0xE5
    # data[32] : 0xE6
    # data[33] : 0xE7

    self._trim_t1 = struct.unpack("H", struct.pack("H", (data[1] << 8) | (data[0])))[0]
    self._trim_t2 = struct.unpack("h", struct.pack("H", (data[3] << 8) | (data[2])))[0]
    self._trim_t3 = struct.unpack("h", struct.pack("H", (data[5] << 8) | (data[4])))[0]

    self._trim_p1 = struct.unpack("H", struct.pack("H", (data[7] << 8) | (data[6])))[0]
    self._trim_p2 = struct.unpack("h", struct.pack("H", (data[9] << 8) | (data[8])))[0]
    self._trim_p3 = struct.unpack("h", struct.pack("H", (data[11] << 8) | (data[10])))[0]
    self._trim_p4 = struct.unpack("h", struct.pack("H", (data[13] << 8) | (data[12])))[0]
    self._trim_p5 = struct.unpack("h", struct.pack("H", (data[15] << 8) | (data[14])))[0]
    self._trim_p6 = struct.unpack("h", struct.pack("H", (data[17] << 8) | (data[16])))[0]
    self._trim_p7 = struct.unpack("h", struct.pack("H", (data[19] << 8) | (data[18])))[0]
    self._trim_p8 = struct.unpack("h", struct.pack("H", (data[21] << 8) | (data[20])))[0]
    self._trim_p9 = struct.unpack("h", struct.pack("H", (data[23] << 8) | (data[22])))[0]

    self._trim_h1 = struct.unpack("B", struct.pack("B", (data[25])))[0]
    self._trim_h2 = struct.unpack("h", struct.pack("H", (data[28] << 8) | (data[27])))[0]
    self._trim_h3 = struct.unpack("B", struct.pack("B", (data[29])))[0]
    self._trim_h4 = struct.unpack("h", struct.pack("H", (data[30] << 4) | (data[31] & 0x0F)))[0]
    self._trim_h5 = struct.unpack("h", struct.pack("H", (data[32] << 4) | (data[31] >> 4)))[0]
    self._trim_h6 = struct.unpack("b", struct.pack("B", (data[33])))[0]


  # returns (humidity, temperature, pressure)
  # must have non-zero modes to be included

  def _get_data_sensor(self):

    # read the whole data block

    data = self._xm.i2c_read(self._addr, 0xF7, 8)

    # calculate

    tmp_h = 0
    tmp_t = 0
    tmp_p = 0

    if self._mode_h > 0x00:

      # humidity:
      #  0xFD[0:7] -> [8:15]
      #  0xFE[0:7] -> [0:7]

      tmp_h = (data[6] << 8) | data[7]

    if self._mode_t > 0x00:

      # temperature:
      #   0xFA[0:7] -> [12:19]
      #   0xFB[0:7] -> [4:11]
      #   0xFC[4:7] -> [0:3]

      tmp_t = ((data[3] << 16) | (data[4] << 8) | data[5]) >> 4

    if self._mode_p > 0x00:

      # pressure:
      #   0xF7[0:7] -> [12:19]
      #   0xF8[0:7] -> [4:11]
      #   0xF9[4:7] -> [0:3]

      tmp_p = ((data[0] << 16) | (data[1] << 8) | data[2]) >> 4

    return (tmp_h, tmp_t, tmp_p)


  # returns tuple of booleans: (chip-ready, data-ready)

  def _get_status(self):

    status = self._xm.i2c_read(self._addr, 0xF3, 1)[0]

    return ((status & 0x01) == 0x00, (status & 0x08) == 0x00)


  # mode_h, mode_t and mode_p:
  #   0x00 = disabled
  #   0x01 = x1 oversampling
  #   0x02 = x2 oversampling
  #   0x03 = x4 oversampling
  #   0x04 = x8 oversampling
  #   0x05 = x16 oversampling

  # mode:
  #   0x00 = sleep
  #   0x01 = forced (one shot)
  #   0x02 = forced (one shot)
  #   0x03 = normal (continuous/cyclic)

  def _set_mode(self, mode_h=None, mode_t=None, mode_p=None, mode=None):

    if mode_h == None:
      # only enable humidity probe by default if sensor is a BME280
      if self._chip_id == 0x60:
        self._mode_h = 0x30
      else:
        self._mode_h = 0x00
    else:
      self._mode_h = self._normalise(mode_h, 0x00, 0x05)

    if mode_t == None:
      self._mode_t = 0x30
    else:
      self._mode_t = self._normalise(mode_t, 0x00, 0x05)

    if mode_p == None:
      self._mode_p = 0x30
    else:
      self._mode_p = self._normalise(mode_p, 0x00, 0x05)

    if mode == None:
      mode = 0x00
    else:
      self._mode = self._normalise(mode, 0x00, 0x03)

    self._xm.i2c_write(self._addr, 0xF2, [self._mode_h])
    self._xm.i2c_write(self._addr, 0xF4, [((self._mode_t & 0x07) << 5) | ((self._mode_p & 0x07) << 2) | (self._mode & 0x03)])


  # standby: (applicable only when mode == 0x03):
  #   0x00 =    0.5 ms
  #   0x01 =   62.5 ms
  #   0x02 =  125.0 ms
  #   0x03 =  250.0 ms
  #   0x04 =  500.0 ms
  #   0x05 = 1000.0 ms
  #   0x06 =   10.0 ms (bme280); 2000.0 ms (bmp280)
  #   0x07 =   20.0 ms (bme280); 4000.0 ms (bmp280)

  # irfilter values:
  #   0x00 = disabled
  #   0x01 = filter coefficient =  2
  #   0x02 = filter coefficient =  4
  #   0x03 = filter coefficient =  8
  #   0x04 = filter coefficient = 16

  def _set_config(self, standby=0x05, irfilter=0x1):

    standby = self._normalise(standby, 0x00, 0x07)
    irfilter = self._normalise(irfilter, 0x00, 0x07)

    # needed for calculating tstandby

    self._standby = standby

    self._xm.i2c_write(self._addr, 0xF5, [((standby & 0x07) << 5) | ((irfilter & 0x07) << 2)])


  def _normalise(self, val, val_min, val_max):

    if val < val_min:
      return val_min

    if val > val_max:
      return val_max

    return val


  # apply Bosch's pressure compensation formulas for 32-bit ints

  def _adjust_data(self, raw_h, raw_t, raw_p):

    tmp_h = 0.0
    tmp_t = 0.0
    tmp_p = 0.0

    # t_fine

    v1 = ((raw_t >> 3) - (self._trim_t1 << 1)) * (self._trim_t2 >> 11)
    v2 = (((((raw_t >> 4) - self._trim_t1) * ((raw_t >> 4) - self._trim_t1)) >> 12) * self._trim_t3) >> 14;

    t_fine = v1 + v2

    # humidity

    if self._mode_h:

      tmp_h = t_fine - 76800
      tmp_h = ((((raw_h << 14) - (self._trim_h4 << 20) - (self._trim_h5 * tmp_h)) + 16384) >> 15) * (((((((tmp_h * self._trim_h6) >> 10) * (((tmp_h * self._trim_h3) >> 11) + 32768)) >> 10) + 2097152) * self._trim_h2 + 8192) >> 14)
      tmp_h = tmp_h - (((((tmp_h >> 15) * (tmp_h >> 15)) >> 7) *  self._trim_h1) >> 4)
      tmp_h = self._normalise(tmp_h, 0, 419430400) >> 12

    # temperature

    if self._mode_t:

      tmp_t = (t_fine * 5 + 128) >> 8

    # pressure

    if self._mode_p:

      v1 = ((t_fine) >> 1) - 64000
  
      v2 = (((v1 >> 2) * (v1 >> 2)) >> 11) * self._trim_p6
      v2 = v2 + ((v1 * self._trim_p5) << 1)
      v2 = (v2 >> 2) + (self._trim_p4 << 16)
  
      v1 = (((self._trim_p3 * (((v1 >> 2) * (v1 >> 2)) >> 13)) >> 3) + ((self._trim_p2 * v1) >> 1)) >> 18;
      v1 = ((((32768 + v1)) * (self._trim_p1)) >> 15);
  
      if v1 != 0:
  
        tmp_p = (((1048576 - raw_p) - (v2 >> 12))) * 3125
  
        if tmp_p < 0x80000000:
          tmp_p = (tmp_p << 1) // v1
        else:
          tmp_p = (tmp_p // v1) * 2
      
        v1 = (self._trim_p9 * ((((tmp_p >> 3) * (tmp_p >> 3)) >> 13))) >> 12
  
        v2 = (((tmp_p >> 2)) * self._trim_p8) >> 13
  
        tmp_p = (tmp_p + ((v1 + v2 + self._trim_p7) >> 4))

    return (tmp_h / 1024.0, tmp_t / 100.0, tmp_p / 100.0)


  # calculate and return maximum time in microseconds that it will take the
  # sensor to make measurement based on current modes

  def _get_tmeasure(self):

    mtime = 0

    if self._mode_h > 0:
      mtime = mtime + (2300 * (1 << self._mode_h) + 575)

    if self._mode_t > 0:
      mtime = mtime + (2300 * (1 << self._mode_t))

    if self._mode_p > 0:
      mtime = mtime + (2300 * (1 << self._mode_p) + 575)

    # mtime will still be zero at this point if all measurements were disabled
    # add an extra 1.25 msec if we are doing at least one measurement

    if mtime > 0:
      mtime = mtime + 1250

    return mtime


  # interval between measurements in microseconds

  def _get_tstandby(self):

    mtime = 0

    if self._mode == 0x03:
      # use alternate map for non-BME280 chips
      if self._chip_id == 0x60:
        mtime = BME280_TSTANDBY_MAP[self._standby]
      else:
        mtime = BME280_TSTANDBY2_MAP[self._standby]

    return mtime


  # send reset command; block until ready

  def reset(self):

    self._xm.i2c_write(self._addr, 0xE0, [0xB6])

    while not self._get_status()[0]:
      self._xt.sleep_ms(1)

    self._get_data_rom()
    self._set_config()
    self._set_mode()


  # set sensor modes
  #   oversampling: 1, 2, 4, 8, 16
  #   continuous:
  #           0 = single-shot mode
  #         500 =    0.5 msecs
  #       62500 =   62.5 msecs
  #      125000 =  125.0 msecs
  #      250000 =  250.0 msecs
  #      500000 =  500.0 msecs
  #     1000000 = 1000.0 msecs
  #       10000 =   10.0 msecs (BME280 only)
  #       20000 =   20.0 msecs (BME280 only)
  #     2000000 = 2000.0 msecs (BMP280 only)
  #     4000000 = 4000.0 msecs (BMP280 only)

  def set(self, oversampling=None, continuous=None):

    # oversampling: if None or invalid, use current

    mode_h = self._mode_h
    mode_t = self._mode_t
    mode_p = self._mode_p

    # otherwise, use it to get the corresponding index

    if oversampling != None and oversampling != 0 and oversampling in BME280_OVERSAMPLING_MAP.values():
      oindex = {y: x for x, y in BME280_OVERSAMPLING_MAP.items()}[oversampling]
      mode_h = oindex
      mode_t = oindex
      mode_p = oindex

    # always set sleep mode first

    self._set_mode(mode_h, mode_t, mode_p, 0x00)

    # use appropriate map depending on chip

    smap = BME280_TSTANDBY_MAP if self._chip_id == 0x60 else BME280_TSTANDBY2_MAP

    # were we asked to go in continuous mode?

    if continuous != None and continuous > 0 and continuous in smap.values():

      sindex = {y: x for x, y in smap.items()}[continuous]
      self._set_config(standby=sindex)
      self._set_mode(mode_h, mode_t, mode_p, 0x03)

      # absolute time until expiry

      self._time_ready = self._xt.time_us() + self._get_tmeasure() + self._get_tstandby()


  # returns a tuple: (relative  humidity, temperature, pressure)

  def get(self):

    if self._mode == 0x03:

      # in continuous mode, block until the next cycle

      delta = self._time_ready - self._xt.time_us()

      if delta > 0:
        self._xt.sleep_us(delta)

    else:

      # if we're in anything other than continuous mode

      # set forced mode

      self._set_mode(self._mode_h, self._mode_t, self._mode_p, 0x01)

      # mandatory wait

      self._xt.sleep_us(self._get_tmeasure())

    # make sure we're ready to read

    while not self._get_status()[1]:
      self._xt.sleep_ms(1)

    # read data and adjust

    data = self._adjust_data(*self._get_data_sensor())

    # in continuous mode, reset time to next cycle

    if self._mode == 0x03:
      self._time_ready = self._xt.time_us() + self._get_tmeasure() + self._get_tstandby()

    return data


  # returns a tuple: (numeric chip ID, chip description string)

  def get_id(self):

    chip_desc = "Unknown"

    if self._chip_id in BME280_ID_MAP.keys():
      chip_desc = BME280_ID_MAP[self._chip_id]

    return (self._chip_id, chip_desc)


  # returns list of valid invervals for use as value to the continuous parameter in set()

  def get_intervals(self, chip_id=None):

    if chip_id == None:
      chip_id = self._chip_id 

    return sorted((BME280_TSTANDBY_MAP if chip_id == 0x60 else BME280_TSTANDBY2_MAP).values())


  # returns list of valid values for use as value to the oversampling  parameter in set()

  def get_oversampling(self):

    return sorted(filter(lambda x: x > 0, BME280_OVERSAMPLING_MAP.values()))
