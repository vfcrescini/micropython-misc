#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-07-15 mpu6050.py

# ver basic MPU-6050 I2C driver 
# Data from:
#  https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf
#  https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf


import struct


# accelerometer range (g)

MPU6050_RANGEA_MAP = {
  0x00:     2,
  0x01:     4,
  0x02:     8,
  0x03:    16
}

# accelerometer sensitivity scale factor (g/val)

MPU6050_SCALEA_MAP = {
  0x00:     60,
  0x01:    120,
  0x02:    240,
  0x03:    490
}

# gyroscope range (%/s)

MPU6050_RANGEG_MAP = {
  0x00:    250,
  0x01:    500,
  0x02:   1000,
  0x03:   2000
}

# gyroscope sensitivity scale factor (1000*val/%/s)

MPU6050_SCALEG_MAP = {
  0x00: 131000,
  0x01:  65500, 
  0x02:  32800,
  0x03:  16400
}

# default number of samples to use for calibration

MPU6050_DEFAULT_CALIBRATION_SAMPLES = 500


class MPU6050:

  def __init__(self, xm, xt, addr=0x68):

    self._xm = xm
    self._xt = xt
    self._addr = addr

    self._isens_a = 0x00
    self._isens_g = 0x01

    self.reset()


  def _normalise(self, val, val_min, val_max):

    if val < val_min:
      return val_min

    if val > val_max:
      return val_max

    return val


  # isens_a (accelerometer mode):
  #   0x00 = +-  2 g
  #   0x01 = +-  4 g
  #   0x02 = +-  8 g
  #   0x03 = +- 16 g

  # isens_g (gyrosope mode):
  #   0x00 = +-  250 deg/sec
  #   0x01 = +-  500 deg/sec
  #   0x02 = +- 1000 deg/sec
  #   0x03 = +- 2000 deg/sec


  def _set(self, isens_a=None, isens_g=None):

    if isens_a == None:
      self._isens_a = 0x00
    else:
      self._isens_a = self._normalise(isens_a, 0x00, 0x03)

    if isens_g == None:
      self._isens_g = 0x00
    else:
      self._isens_g = self._normalise(isens_g, 0x00, 0x03)

    self._xm.i2c_write(self._addr, 0x1C, [ self._isens_a << 3 ])
    self._xm.i2c_write(self._addr, 0x1B, [ self._isens_g << 3 ])


  def _get_data_a(self):

    ax = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x3B, 2)))[0]
    ay = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x3D, 2)))[0]
    az = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x3F, 2)))[0]

    return ax, ay, az


  def _get_data_g(self):

    gx = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x43, 2)))[0]
    gy = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x45, 2)))[0]
    gz = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x47, 2)))[0]

    return gx, gy, gz


  def _get_data_t(self):

    t = struct.unpack(">h", bytes(self._xm.i2c_read(self._addr, 0x41, 2)))[0]

    return t


  def _calibrate(self, samples):

    tgx = 0
    tgy = 0
    tgz = 0

    for i in range(0, samples):

      gx, gy, gz = self._get_data_g()

      tgx = tgx + gx
      tgy = tgy + gy
      tgz = tgz + gz

      self._xt.sleep_ms(1)

    self._calib_gx = tgx / samples
    self._calib_gy = tgy / samples
    self._calib_gz = tgz / samples


  # reset device
  #   csamples:
  #     0: no calibration
  #     n > 0: calibrate using n samples

  def reset(self, csamples=MPU6050_DEFAULT_CALIBRATION_SAMPLES):

    self._xm.i2c_write(self._addr, 0x6B, [0x40])
    self._xt.sleep_ms(100)
    self._xm.i2c_write(self._addr, 0x6B, [0x00])
    self._xt.sleep_ms(10)

    self._set()

    self._calib_gx = 0.0
    self._calib_gy = 0.0
    self._calib_gz = 0.0

    if csamples > 0:
      self._calibrate(csamples)


  # set sensor sensitivity

  # sens_a:
  #   2
  #   4
  #   8
  #  16

  # sens_g:
  #   250
  #   500
  #  1000
  #  2000

  def set(self, sens_a=None, sens_g=None):

    isens_a = self._isens_a
    isens_g = self._isens_g

    # build temporary reverse dict to find the correct index from given value

    mapa = {y: x for x, y in MPU6050_RANGEA_MAP.items()}
    mapg = {y: x for x, y in MPU6050_RANGEG_MAP.items()}

    if sens_a != None and sens_a in mapa:
      isens_a = mapa[sens_a]

    if sens_g != None and sens_g in mapg:
      isens_g = mapg[sens_g]

    # set mode

    self._set(isens_a, isens_g)


  # get accelerometer values

  def get_a(self):

    ax, ay, az = self._get_data_a()

    ax = ax * MPU6050_SCALEA_MAP[self._isens_a] / 1000000
    ay = ay * MPU6050_SCALEA_MAP[self._isens_a] / 1000000
    az = az * MPU6050_SCALEA_MAP[self._isens_a] / 1000000

    return ax, ay, az


  # get gyroscope values

  def get_g(self):

    gx, gy, gz = self._get_data_g()

    gx = (gx - self._calib_gx) * 1000 / MPU6050_SCALEG_MAP[self._isens_g]
    gy = (gy - self._calib_gy) * 1000 / MPU6050_SCALEG_MAP[self._isens_g]
    gz = (gz - self._calib_gz) * 1000 / MPU6050_SCALEG_MAP[self._isens_g]

    return gx, gy, gz


  # get temperature value

  def get_t(self):

    return self._get_data_t() / 340 + 36.53


  # get all

  def get(self):

    return self.get_a() + self.get_g() + (self.get_t(), )
