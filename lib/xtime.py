#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-19 xtime.py

# convenience library to provide a unified time API on both micropython and cpython
# micropython localtime() uses custom tzdata file
# tzdata file line format: <seconds since embedded epoch> <utc offset in seconds>


import sys as _sys
import time as _time
import re as _re


EPOCH_OFFSET = 946684800

_DEFAULT_TZ_FILE_PATH = "tzdata.txt"
_EPOCH_OFFSET = EPOCH_OFFSET if _sys.platform.lower().startswith("linux") or _sys.platform.lower().startswith("rp2") else 0


class XTime(object):


  def __new__(cls, *args, **kwargs):

    xt = None

    if cls == XTime:

      # we're instantiating XTime, so return an instance of one of the subclasses instead

      if hasattr(_sys, "implementation") and _sys.implementation.name == "micropython":
        xt = _XTimeMicroPython(*args, **kwargs)
      else:
        xt = _XTimeCPython(*args, **kwargs)

    else:

      # we're instantiating one of the subclasses, so just do what __new__() normally does

      xt = object.__new__(cls)

    return xt


  def __init__(self, *args, **kwargs):

    pass


  def sleep_ns(self, nsecs):

    raise NotImplementedError


  def sleep_us(self, usecs):

    raise NotImplementedError


  def sleep_ms(self, msecs):

    raise NotImplementedError


  def sleep_ss(self, ssecs):

    raise NotImplementedError


  def time_ns(self):

    raise NotImplementedError


  def time_us(self):

    raise NotImplementedError


  def time_ms(self):

    raise NotImplementedError


  def time_ss(self):

    raise NotImplementedError


  def localtime(self, ssecs=None):

    raise NotImplementedError


  def mktime(self, ttuple):

    raise NotImplementedError


  def gmtime(self, ssecs=None):

    raise NotImplementedError


class _XTimeCPython(object):

  def __init__(self):

    pass


  def sleep_ns(self, nsecs):

    raise NotImplementedError


  def sleep_us(self, usecs):

    self.sleep_ms(usecs / 1000.0)


  def sleep_ms(self, msecs):

    self.sleep_ss(msecs / 1000.0)


  def sleep_ss(self, ssecs):

    _time.sleep(ssecs)


  def time_ns(self):

    return int((_time.time() - _EPOCH_OFFSET) * 1000000000)


  def time_us(self):

    return self.time_ns() // 1000


  def time_ms(self):

    return self.time_us() // 1000


  def time_ss(self):

    return int(_time.time() - _EPOCH_OFFSET)


  def localtime(self, ssecs=None):

    if ssecs == None:
      ssecs = self.time_ss()

    t = _time.localtime(ssecs + _EPOCH_OFFSET)

    return t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday, t.tm_yday


  def mktime(self, ttuple):

    return int(_time.mktime(ttuple + (-1,))) - _EPOCH_OFFSET


  def gmtime(self, ssecs=None):

    if ssecs == None:
      ssecs = self.time_ss()

    t = _time.gmtime(ssecs + _EPOCH_OFFSET)

    return t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday, t.tm_yday


class _XTimeMicroPython(object):


  _tz_line_pattern = _re.compile("^\s*([0-9]+)\s+([+-]?[0-9]+)\s*$")


  def __init__(self, tz_path=_DEFAULT_TZ_FILE_PATH):

    self._tz_path = tz_path

    self._tz_offset = 0
    self._tz_expiry = 0


  def _update(self, ssecs):

    # if no tzdata file was set, do nothing

    if self._tz_path == None:
      return

    # open the tzdata file
    # let it raise an exception on error
  
    f = open(self._tz_path, "r")
  
    # read each line, ignore everything that is not something space something
    # get only what is relevant, namely, the last line whose timestamp is less than now, and the line after that
  
    prev = None
    curr = None
  
    for line in f:
  
      mo = _XTimeMicroPython._tz_line_pattern.match(line)
  
      if mo == None:
        continue
  
      ttstamp = 0
      toffset = 0
  
      try:
        ttstamp = int(mo.group(1))
        toffset = int(mo.group(2))
      except:
        continue
  
      prev = curr
      curr = ttstamp, toffset
  
      if ssecs < ttstamp:
        break
  
    # we don't need the file anymore
  
    f.close()
  
    # now update the globals
  
    self._tz_offset = 0
    self._tz_expiry = 0
  
    # the expiry of an offset is the in-effect timestamp of the next offset
  
    if prev != None:
      self._tz_offset = prev[1]
  
    if curr != None:
  
      # last one may not actually be expired yet
  
      if ssecs >= curr[0]:
        self._tz_offset = curr[1]
      else:
        self._tz_expiry = curr[0]


  def sleep_ns(self, nsecs):

    raise NotImplementedError


  def sleep_us(self, usecs):

    _time.sleep_us(usecs)


  def sleep_ms(self, msecs):

    _time.sleep_ms(msecs)


  def sleep_ss(self, ssecs):

    _time.sleep(ssecs)


  def time_ns(self):

    return _time.time_ns() - (_EPOCH_OFFSET * 1000000000)


  def time_us(self):

    return self.time_ns() // 1000


  def time_ms(self):

    return self.time_us() // 1000


  def time_ss(self):

    return int(_time.time()) - _EPOCH_OFFSET


  def localtime(self, ssecs=None):

    if ssecs == None:
      ssecs = self.time_ss()

    # if the current tzdata offset is expired, try to update it

    if self._tz_expiry <= ssecs:
      self._update(ssecs)

    return _time.localtime(ssecs + _EPOCH_OFFSET)[:8]


  def mktime(self, ttuple):

    return _time.mktime(ttuple) - _EPOCH_OFFSET


  def gmtime(self, ssecs=None):

    if ssecs == None:
      ssecs = self.time_ss()

    return _time.gmtime(ssecs + _EPOCH_OFFSET)[:8]
