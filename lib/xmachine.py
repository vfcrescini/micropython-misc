#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-27 xmachine.py

# wrapper library to provide a unified I2C API on both micropython and cpython


import sys as _sys

if hasattr(_sys, "implementation") and _sys.implementation.name == "micropython":
  import machine
else:
  import smbus


class XMachine(object):


  def __new__(cls, *args, **kwargs):

    xm = None

    if cls == XMachine:

      # we're instantiating XMachine, so return an instance of one of the subclasses instead

      if "machine" in globals():
        xm = _XMachineMicroPython(*args, **kwargs)
      else:
        xm = _XMachineCPython(*args, **kwargs)

    else:

      # we're instantiating one of the subclasses, so just do what __new__() normally does

      xm = object.__new__(cls)

    return xm


  def __init__(self, *args, **kwargs):
    pass


  def i2c_read(self, addr, register, nbytes):
    raise NotImplementedError


  def i2c_write(self, addr, register, data):
    raise NotImplementedError


  def i2c_read_byte(self, addr):
    raise NotImplementedError


  def i2c_write_byte(self, addr, data):
    raise NotImplementedError


  def i2c_read_bytes(self, addr, nbytes):
    raise NotImplementedError


  def i2c_write_bytes(self, addr, data):
    raise NotImplementedError


class _XMachineCPython(XMachine):


  def __init__(self, bus=None):

    if bus == None:
      raise ValueError("bus ID is required")

    self._i2cbus = smbus.SMBus(bus)


  def i2c_read(self, addr, register, nbytes):

    return self._i2cbus.read_i2c_block_data(addr, register, nbytes)


  def i2c_write(self, addr, register, data):

    self._i2cbus.write_i2c_block_data(addr, register, data)


  def i2c_read_byte(self, addr):

    return self._i2cbus.read_byte(addr)


  def i2c_write_byte(self, addr, data):

    self._i2cbus.write_byte(addr, data)


  def i2c_read_bytes(self, addr, nbytes):

    # this causes a command/register 0x00 I2C write before the read

    return self._i2cbus.read_i2c_block_data(addr, 0x00, nbytes)


  def i2c_write_bytes(self, addr, data):

    if len(data) > 0:
      self._i2cbus.write_i2c_block_data(addr, data[0], data[1:])


class _XMachineMicroPython(XMachine):


  def __init__(self, bus=None, sda=None, scl=None):

    if machine.I2C == machine.SoftI2C:

      # no hardware I2C bus

      if sda == None or scl == None:
        raise ValueError("Using software I2C; sda and scl required")

      self._i2cbus = machine.SoftI2C(sda=machine.Pin(sda), scl=machine.Pin(scl))

    else:

      # hardware I2C present

      if bus == None:

        # no bus given, which implies software I2C

        if sda == None or scl == None:
          raise ValueError("Using software I2C; sda and scl required")

        self._i2cbus = machine.SoftI2C(sda=machine.Pin(sda), scl=machine.Pin(scl))

      else:

        # bus given, so hardware I2C

        if sda == None or scl == None:

          # if one pin is missing, ignore the other

          self._i2cbus = machine.I2C(bus)

        else:

          # all was given

          self._i2cbus = machine.I2C(bus, sda=machine.Pin(sda), scl=machine.Pin(scl))


  def i2c_read(self, addr, register, nbytes):

    return list(self._i2cbus.readfrom_mem(addr, register, nbytes))


  def i2c_write(self, addr, register, data):

    self._i2cbus.writeto_mem(addr, register, bytearray(data))


  def i2c_read_byte(self, addr):

    return list(self._i2cbus.readfrom(addr, register, 1))[0]


  def i2c_write_byte(self, addr, data):

    self._i2cbus.writeto(addr, bytearray([data]))


  def i2c_read_bytes(self, addr, nbytes):

    return list(self._i2cbus.readfrom(addr, nbytes))


  def i2c_write_bytes(self, addr, data):

    self._i2cbus.writeto(addr, bytearray(data))
