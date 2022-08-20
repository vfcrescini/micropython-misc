#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2021-11-21 webserver.py

# quick-and-dirty tick-based webserver


import socket
import select
import re


_DEFAULT_PORT = 80
_DEFAULT_BACKLOG = 2
_DEFAULT_TIMEOUT = 30000
_DEFAULT_TEMPLATE = "HTTP/1.0 %STATUS%\r\nContent-Type: text/plain; charset=iso-8859-1\r\nContent-Length: %LENGTH%\r\n\r\n%CONTENT%"
_DEFAULT_REQMAP = {"/" : ""}


_re_header = re.compile("^([A-Za-z]+) +(\S+) +(HTTP\/[0-9]+\.[0-9]+)\r\n.*")


class Client(object):

  STATE_RD = 0
  STATE_PR = 1
  STATE_WR = 2
  STATE_XX = 3


  def __init__(self, xt, sock, addr, expiry=0):

    self._xt = xt
    self._sock = sock
    self._poller = select.poll()
    self._addr = addr
    self._ibuf = ""
    self._obuf = ""
    self._state = Client.STATE_RD
    self._expiry = expiry

    self._poller.register(self._sock, select.POLLIN | select.POLLOUT)


  def state(self):

    return self._state


  def expired(self, now=None):

    if self._expiry == 0:
      return False

    # now is msec since epoch

    if now == None:
      now = self._xt.time_ms()
  
    return now >= self._expiry


  def close(self):

    self._sock.close()
    self._ibuf = ""
    self._obuf = ""
    self._state = Client.STATE_XX


  def read(self):

    if self._state != Client.STATE_RD:
      return False

    # read all available data

    while(True):

      pe = ([ x[1] for x in list(self._poller.poll(0)) ] + [ 0 ])[0]

      if pe & select.POLLERR or pe & select.POLLHUP:
        self.close()
        return False

      if pe & select.POLLIN == 0:
        break

      tmp = ""

      try:
        tmp = self._sock.recv(1024).decode("utf-8")
      except Exception as e:
        self.close()
        return False

      if len(tmp) == 0:
        self.close()
        return False

      self._ibuf = self._ibuf + tmp

    # have we read the full header?

    if self._ibuf.endswith("\r\n\r\n"):
      self._state = Client.STATE_PR

    return True


  def process(self, template, reqmap):

    if self._state != Client.STATE_PR:
      return False

    # strip out everything after the first line

    i = self._ibuf.find("\r\n")

    if i > 0:
      self._ibuf = self._ibuf[:i + 2]

    status = ""
    content = ""

    m = _re_header.match(self._ibuf)

    if m == None:
      status = "400 Bad Request"
      content = status
    elif m.group(1) != "GET":
      status = "405 Method Not Allowed"
      content = status
    elif m.group(2) not in reqmap:
      status = "404 Not Found"
      content = status
    else:
      status = "200 OK"
      content = reqmap[m.group(2)]

    self._obuf = template.replace("%STATUS%", status).replace("%LENGTH%", str(len(content))).replace("%CONTENT%", content)
    self._ibuf = ""
    self._state = Client.STATE_WR

    return True


  def write(self):

    if self._state != Client.STATE_WR:
      return False

    # write until done

    while True:

      # are we done yet?

      if len(self._obuf) == 0:
        self.close()
        return True

      pe = ([ x[1] for x in list(self._poller.poll(0)) ] + [ 0 ])[0]

      if pe & select.POLLERR or pe & select.POLLHUP:
        self.close()
        return False

      if pe & select.POLLOUT == 0:
        break

      n = 0

      try:
        n = self._sock.send(self._obuf.encode())
      except Exception as e:
        self.close()
        return False

      if n == 0:
        self.close()
        return False

      self._obuf = self._obuf[n:]

    # there is still data to be written, but the peer is not ready to receive yet

    return True


class Webserver(object):

  def __init__(self, xt, port=_DEFAULT_PORT, backlog=_DEFAULT_BACKLOG, timeout=_DEFAULT_TIMEOUT, template=_DEFAULT_TEMPLATE, reqmap=None):

    if reqmap == None:
      reqmap = _DEFAULT_REQMAP

    self._xt = xt
    self._port = port
    self._backlog = backlog
    self._timeout = timeout
    self._template = template

    self._reqmap = reqmap

    self._clients = []
    self._ssock = None
    self._poller = None


  def start(self):

    self._ssock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self._ssock.bind(socket.getaddrinfo("0", self._port, socket.AF_INET, socket.SOCK_STREAM)[0][-1])
    self._ssock.listen(self._backlog)

    self._poller = select.poll()
    self._poller.register(self._ssock, select.POLLIN)


  def stop(self):

    self._ssock.close()
    self._ssock = None

    for client in filter(lambda x: x.state() != Client.STATE_XX, self._clients):
      client.close()

    for client in list(self._clients):
      self._clients.remove(client)


  # reqmap is assumed to be a dictionary of string path keys and string contenti items, or None
  # now is assumed to be an int representing the millisecs since epoch, or None

  def serve(self, reqmap=None, now=None):

    if self._ssock == None:
      return

    # the actual request map to use is what was given during initalisation (or default), updated
    # with what is given nowwhat was given during initalisation (or default), updated with what
    # is given here

    treqmap = self._reqmap.copy()

    if reqmap != None:
      treqmap.update(reqmap)

    if now == None:
      if self._timeout > 0:
        now = self._xt.time_ms()
      else:
        now = 0

    # accept all pending connections

    while True:
 
      pe = ([ x[1] for x in list(self._poller.poll(0)) ] + [ 0 ])[0]

      if pe & select.POLLIN == 0:
        break

      csock, caddr = self._ssock.accept()
      expiry = 0

      if self._timeout > 0:
        expiry = now + self._timeout

      self._clients.append(Client(self._xt, csock, caddr, expiry))

    # read

    for client in filter(lambda x: x.state() == Client.STATE_RD, self._clients):
      client.read()
  
    # process

    for client in filter(lambda x: x.state() == Client.STATE_PR, self._clients):
      client.process(self._template, treqmap)

    # write

    for client in filter(lambda x: x.state() == Client.STATE_WR, self._clients):
      client.write()

    # close expired

    if self._timeout > 0:
      for client in filter(lambda x: x.expired(), self._clients):
        client.close()

    # clean

    for client in filter(lambda x: x.state() == Client.STATE_XX, self._clients):
      self._clients.remove(client)
