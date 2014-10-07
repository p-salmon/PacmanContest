#!/usr/bin/env python

from httplib2 import Http
from urllib import urlencode

h = Http()


resp, content = h.request("http://www.google.com", "GET")

print(resp)

print("Hello World !")


