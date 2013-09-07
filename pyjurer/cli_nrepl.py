#! /usr/bin/env python
# a python-based nrepl client for clojure

from session_container import create_bcode_over_tcp_session

session = create_bcode_over_tcp_session('localhost', )

