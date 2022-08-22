#!/usr/bin/python3

# Copyright (C) 2022 Vino Fernando Crescini <vfcrescini@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# 2022-08-06 webclient.py

# not-so-quck-but-still-dirty tick-based web client

import errno
import socket
import re


_DEFAULT_PORT = 80
_DEFAULT_METHOD = "GET"

_RECV_BLOCKSIZE = 1024


_re_line = re.compile("\r?\n")
_re_status = re.compile("HTTP/([0-9]+\.[0-9]+) +([0-9][0-9][0-9]) +([^\r\n]*)")
_re_header = re.compile("([A-Za-z][A-Za-z-]*): +([^\r\n]*)")


class HTTPRequest(object):

  STATE_NULL = 0
  STATE_INIT = 1
  STATE_CONN = 2
  STATE_SEND = 3
  STATE_RCV1 = 4
  STATE_RCV2 = 5
  STATE_RCV3 = 6
  STATE_DONE = 100
  STATE_ERROR = 1000

  def __init__(self):

    self._addr = None
    self._path = None
    self._method = _DEFAULT_METHOD

    self._buf = ""
    self._state = HTTPRequest.STATE_NULL
    self._socket = None

    self._rsp_status = (0, "")
    self._rsp_headers = {}


  # send stuff that are in the buffer
  #  return  0,     _ : success, done
  #  return  1,     _ : success, not done yet
  #  return -1, errno : socket error

  def _send(self):

    if len(self._buf) == 0:
      return 0, 0

    n = 0

    try:
      n = self._socket.send(self._buf)
    except Exception as e:
      if hasattr(e, "errno"):
        if e.errno == errno.EAGAIN:
          return 1, 0
        return -1, e.errno
      return -1, 0

    # this should never happen, but check anyway

    if n == 0:
      return -1, 0

    # remove from buffer what we've just sent

    self._buf = self._buf[n:]

    return 0, 0


  # receive stuff into the buffer
  #  return  0,   EOF : success
  #  return  1,     _ : success, not done yet
  #  return -1, errno : socket error

  def _recv(self, blocksize=0):

    if blocksize <= 0 or blocksize > _RECV_BLOCKSIZE:
      blocksize=_RECV_BLOCKSIZE

    t = ""
  
    try:
      t = self._socket.recv(blocksize)
    except Exception as e:
      if hasattr(e, "errno"):
        if e.errno == errno.EAGAIN or e.errno:
          return 1, 0
        return -1, e.errno
      return -1, 0
  
    # put on buffer what we've just received

    if len(t) > 0:
      self._buf = self._buf + t.decode("utf-8")

    return 0, len(t) == 0


  # consume status line from buffer
  #   return  0 : success
  #   return  1 : we don't have a full line yet
  #   return -1 : error

  def _consume_status(self):

    t = _re_line.split(self._buf, 1)

    if len(t) == 1:
      return 1

    # we got a full line; remove from buffer

    self._buf = t[1]

    # is it a valid status line?

    t = _re_status.match(t[0])

    if t == None:
      return -1

    self._rsp_status = (int(t.group(2)), t.group(3))

    return 0


  # consume status line from buffer
  #   return  0 : success
  #   return  1 : we don't have a full line yet
  #   return -1 : error

  def _consume_headers(self):

    while True:

      t = _re_line.split(self._buf, 1)
      
      if len(t) == 1:
        return 1
      
      # we got a full line; remove from buffer
      
      self._buf = t[1]

      # are we at the end of the header section?

      if len(t[0]) == 0:
        break;
      
      # is it a valid header line?
      
      t = _re_header.match(t[0])
      
      if t == None:
        return -1
      
      self._rsp_headers[t.group(1).lower()] = t.group(2)
      
    return 0


  def set(self, host, path, port=_DEFAULT_PORT, method=_DEFAULT_METHOD):

    self._state = HTTPRequest.STATE_NULL

    # we only support GET for now

    if method != "GET":
      return 1

    # did we get valid host and port?

    addr = None

    try:
      addr = socket.getaddrinfo(host, port)[0][-1]
    except:
      return 2

    # everything else

    self._addr = addr
    self._path = path

    self._state = HTTPRequest.STATE_INIT

    self.reset()

    return 0


  def reset(self):

    if self._state <= HTTPRequest.STATE_NULL:
      return 1

    try:
      self._socket.close()
    except:
      pass

    self._rsp_status = (0, "")
    self._rsp_headers = {}

    self._buf = ("%s %s HTTP/1.0\r\n\r\n" % (self._method, self._path)).encode()
    self._state = HTTPRequest.STATE_INIT
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    self._socket.setblocking(0)

    return 0


  # connect, send request, receive response
  #   return rv, state, error-message
  #     rv:
  #       = 0 : ok
  #       > 0 : recoverable error
  #       < 0 : unrecoverable error
  #    state:
  #      %d
  #    error-message:
  #      %s

  def request(self):

    while True:

      if self._state == HTTPRequest.STATE_NULL:

        return 1, self._state, "Request not initialised"

      elif self._state == HTTPRequest.STATE_INIT:

        # initiate connection

        try:
          self._socket.connect(self._addr)
        except Exception as e:
          if hasattr(e, "errno") and e.errno == errno.EINPROGRESS:
            self._state = HTTPRequest.STATE_CONN
            return 0, self._state, ""

          self._state = HTTPRequest.STATE_ERROR
          return -1, self._state, "connect() failed: %s" % (e)

        self._state = HTTPRequest.STATE_SEND

      elif self._state == HTTPRequest.STATE_CONN:

        # connection has been initiated; make sure it goes through
        # we could select() or poll(), but simpler to just attempt
        # a zero-byte send()

        try:
          self._socket.send(b"")
        except Exception as e:
          if hasattr(e, "errno"):
            if e.errno == errno.EAGAIN:
              return 0, self._state, ""

          return -2, self._state, "send() failed: %s" % (e)

        # connected! proceed to the next step

        self._state = HTTPRequest.STATE_SEND

      elif self._state == HTTPRequest.STATE_SEND:

        # send request

        rv, e = self._send()

        if rv < 0:
          self._state = HTTPRequest.STATE_ERROR
          return -3, self._state, ":send() %s" % (errno.errcode[e] if e in errno.errcode else "unknown")

        if rv > 0:
          return 0, self._state, ""

        # request sent

        self._state = HTTPRequest.STATE_RCV1
        self._buf = ""

      elif self._state == HTTPRequest.STATE_RCV1:

        # is there a full status line in the buffer?

        rv = self._consume_status()

        # error?

        if rv < 0:
          self._state = HTTPRequest.STATE_ERROR
          return -4, self._state, "Failed to decode HTTP status line"

        # not a full line yet? get more bytes

        if rv > 0:
          rv, e = self._recv()

          if rv < 0:
            self._state = HTTPRequest.STATE_ERROR
            return -5, self._state, "recv() failed: %s" % (errno.errcode[e] if e in errno.errcode else "unknown")

          if rv > 0:
            return 0, self._state, ""

          if rv == 0 and e:
            self._state = HTTPRequest.STATE_ERROR
            return -6, self._state, "recv() failed: premature EOF"

          continue

        # status received; proceed to headers

        self._state = HTTPRequest.STATE_RCV2

      elif self._state == HTTPRequest.STATE_RCV2:

        # are there header lines in the buffer?

        rv = self._consume_headers()

        # error?

        if rv < 0:
          self._state = HTTPRequest.STATE_ERROR
          return -7, self._state, "Failed to decode HTTP header lines"

        # not done yet? get more bytes

        if rv > 0:
          rv, e = self._recv()

          if rv < 0:
            self._state = HTTPRequest.STATE_ERROR
            return -8, self._state, "recv() failed: %s" % (errno.errcode[e] if e in errno.errcode else "unknown")

          if rv > 0:
            return 0, self._state, ""

          if rv == 0 and e:
            self._state = HTTPRequest.STATE_ERROR
            return -9, self._state, "recv() failed: premature EOF"

          continue

        # headers received; proceed to body

        self._state = HTTPRequest.STATE_RCV3

      elif self._state == HTTPRequest.STATE_RCV3:

        # were we given content-length?

        blen = int(self._rsp_headers["content-length"]) if "content-length" in self._rsp_headers else 0

        rv, e = self._recv(blen)

        if rv < 0:
          self._state = HTTPRequest.STATE_ERROR
          return -10, self._state, "recv() failed: %s" % (errno.errcode[e] if e in errno.errcode else "unknown")

        if rv > 0:
          return 0, self._state, ""

        # are we done?
        # we are, if response had content-length and we've read at least as much
        # or, response didn't, and we've seen EOF

        if (blen > 0 and len(self._buf) >= blen) or (blen == 0 and e):

          self._state = HTTPRequest.STATE_DONE
          return 0, self._state, ""

        # not done yet if response had content-length and we haven't read as
        # much and we haven't seen EOF, or response had no content-length and
        # we haven't seen EOF

        if (blen > 0 and len(self._buf) < blen and not e) or (blen == 0 and not e):
          continue

        # all other cases are error conditions

        self._state = HTTPRequest.STATE_ERROR
        return -11, self._state, "Failed to read response body"

      elif self._state == HTTPRequest.STATE_DONE:

        return 0, self._state, ""

      else:

        # unknown state; shouldn't happen

        return 2, self._state, "Invalid state"


  # get response after state is STATE_DONE
  # return status, headers, body
  #   status:
  #     (%d, %s)
  #   headers:
  #     { %s: %s, ... }
  #   body:
  #     %s

  def get_response(self):

    if self._state != HTTPRequest.STATE_DONE:
      return (0, ""), {}, ""

    return self._rsp_status, self._rsp_headers, self._buf
