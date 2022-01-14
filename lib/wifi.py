#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-18 wifi.py

# wifi helper

import os
import network
import time


# read in wifi credentials

def get_cred(path="wifi.txt", verbose=False):

  f = None
  l = None

  if path not in os.listdir():
    if verbose:
      print("[wifi] unable to find %s" % (path))
    return (None, None)

  try:
    f = open(path, "r")
  except:
    if verbose:
      print("[wifi] unable to open %s" % (path))
    return (None, None)

  try:
    l = f.readlines()
  except:
    if verbose:
      print("[wifi] unable to read %s" % (path))
    return (None, None)

  f.close()

  return tuple(map(lambda x: x.strip(), l))


# connect to WIFI

def connect(path="wifi.txt", verbose=False):

  found = False
  net = network.WLAN(network.STA_IF)
  essid, passwd = get_cred(path, verbose)

  net.active(False)
  time.sleep(1)
  net.active(True)

  # dump wifi scan

  for sessid in map(lambda x: str(x[0], "utf-8"),  net.scan()):

    if verbose:
      print("[wifi] found ap: %s" % (sessid))

    if sessid == essid:
      found = True

  # did we find the one we want?

  if not found:
    if verbose:
      print("[wifi] unable to find %s" % (essid))
    return False

  # connect

  if verbose:
    print("[wifi] connecting to %s..." %  (essid))

  net.connect(essid, passwd)

  for i in range(1, 30):

    if net.isconnected():

      if verbose:
        print("[wifi] connected")

      params = net.ifconfig()

      if verbose:
        print("[wifi] ip:      %s" % params[0])
        print("[wifi] subnet:  %s" % params[1])
        print("[wifi] gateway: %s" % params[2])
        print("[wifi] dns:     %s" % params[3])

      return True

    time.sleep(1)

  if verbose:
    print("[wifi] connect failed")

  return False
