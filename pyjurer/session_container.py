#! /usr/bin/env python

import unittest

class SessionContainer(object):
	'''a nrepl-aware container for logic dealing with nrepl sessions.

	this presents a callback-based api for interacting with nrepl'''

	def __init__(self, sender, idGenerator):
		'''creates a session container

		sender => a function of one param that accepts python data for sending via the transport
		idGenerator => an iterator that creates unique strings used for identifying nrepl instructions'''

		self._sender = sender
		self._idGen = idGenerator

		self._newSessionCallbacks = {}
		self._sessions = {}

	def create_new_session(self, newSessionCb):
		'''creates a new session and returns it with the callback method

		>>> import itertools
		>>> idGenerator = (str(i) for i in itertools.count(1))
		>>> def sender(data):
		...    print data
		>>> def new_session_cb():
		...     pass
		>>> session = SessionContainer(sender, idGenerator)
		>>> session.create_new_session(new_session_cb)
		{'id': '1', 'op': 'clone'}

		'''

		newSessionsId = self._idGen.next()
		self._newSessionCallbacks[newSessionsId] = newSessionCb

		data = {
			'op': 'clone',
			'id': newSessionsId
		}

		self._sender(data)

	def handleNewSessionResponse(self, data, callback):
		'''called when data is received that is a result of requesting a new session'''

		if not 'new-session' in data:
			raise ValueErrro('data must contain new-session')

		newSessionId = data['new-session']
		newSession = NREPLSession(self, newSessionId, self._idGen)
		callback(newSession)


	def acceptData(self, data):
		'''accepts python data straight from the transport

		data => python data structure'''

		if not 'id' in data:
			raise ValueError('data does not contain an "id" field')

		id_ = data['id']

		if id_ in self._newSessionCallbacks:
			handleNewSessionResponse(data, self._newSessionCallbacks.pop(id_))
		else:
			if not 'session' in data:
				raise ValueError('data must contain session, data = {0}'.format(data))

			sessionId = data['session']

			if not sessionId in self._sessions:
				raise ValueError('receiving data for an unregistered session, data = {0}'.format(data))

			self._sessions[sessionId].resultsReceived(data)


	def submit(self, data, session):
		"""Submits data to the channel. 

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""

		if not 'session' in data:
			raise ValueError('data must contain session')

		sessionId = data['session']

		if sessionId != session._sessionId:
			raise ValueError('request for submitting data to session with the wrong session callback') 

		if not sessionId in self._sessions:
			self._sessions[sessionId] = session

		self._sender(data)


if __name__ == "__main__":
	import doctest
	doctest.testmod()

