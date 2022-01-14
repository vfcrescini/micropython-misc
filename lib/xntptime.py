#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-12-15 xntpdate.py

# micropython ntptime convenience wrapper


import sys as _sys

if hasattr(_sys, "implementation") and _sys.implementation.name == "micropython" and not _sys.platform.lower().startswith("linux"):
  import ntptime as _ntptime


_DEFAULT_NTP_HOST = "pool.ntp.org"


# synchronise time with given ntp server
# assumes network connectivity, obviously

def update(ntp_host=_DEFAULT_NTP_HOST, attempts=8):

  if "_ntptime" not in globals():
    return False

  _ntptime.host = ntp_host

  ok = False

  for i in range(0, attempts):
    try:
      _ntptime.settime()
    except:
      pass
    else:
      ok = True
      break

  return ok
