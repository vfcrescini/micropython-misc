#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-01-14 xconfig.py

# very simple name-value configuration parser


class XConfig:

  # path, if given, path to config file
  # config, if given, a dict that contains the initial config params

  def __init__(self, path=None, config=None):

    self._config = {}

    if config != None and isinstance(config, dict):
      self._config = config

    if path !=None:
      self.load(path)


  # parses given config file
  #   path: the path to the config file
  #   returns: True on success, False otherwise

  def load(self, path="config.conf"):

    f = None

    try:
      f = open(path, "r")
    except Exception as e:
      return False

    for line in f:

      line = line.split("#", 1)[0].strip()

      if len(line) == 0:
        continue

      name, value = map(lambda x: x.strip(), line.split('=', 1))

      if len(name) == 0:
        continue

      self._config[name] = value

    try:
      f.close()
    except:
      pass

    return True


  # attempt to retrieve a string config param
  #   name: the name of the config param
  #   default: the string to return if param is not in dict

  def get_str(self, name, default=""):

    value = default

    try:
      value = self._config[name]
    except:
      pass

    return value


  # attempt to retrieve an int config param as an int of the given base
  #   name: the name of the config param
  #   base: base of the int (e.g. 10 for dec, 16 for hex)
  #   default: the int to return if param is not in dict, or is not an int

  def get_int(self, name, base=10, default=0):

    value = default

    try:
      value = int(self._config[name], base)
    except:
      pass

    return value


  # attempt to retrieve a boolean config param
  #   name: the name of the config param
  #   default: the boolean to return if param is not in dict, or is not a bool

  def get_bool(self, name, default=False):

    value = default

    try:
      value = self._config[name].lower() in ["true", "yes", "y"]
    except:
      pass

    return value
