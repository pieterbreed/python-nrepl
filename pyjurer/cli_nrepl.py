#! /usr/bin/env python
# a python-based nrepl client for clojure

from session_container import SessionContainer
import itertools

idGenerator = (str(i) for i in itertools.count(1))

def sender(data):
	print data

def new_session_cb():
	pass

session = SessionContainer(sender, idGenerator)

session.create_new_session(new_session_cb)
