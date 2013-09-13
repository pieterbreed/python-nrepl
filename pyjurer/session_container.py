#! /usr/bin/env python

import unittest, threading, itertools

from channels.tcp import Tcp
from transports.bcode_transport import BCodeTransport
from nrepl_session import NREPLSession
from callback_handler import _CallbackHandler

class SessionContainer(object):
	'''a nrepl-aware container for logic dealing with nrepl sessions.

	this presents a callback-based api for interacting with nrepl'''

	def __init__(self, sender, idGenerator):
		'''creates a session container

		sender => a function of one param that accepts python data for sending via the transport
		idGenerator => an iterator that creates unique strings used for identifying nrepl instructions'''

		self._sender = sender
		self._idGen = idGenerator
		self._newSessionLock = threading.Lock()
		self._newSessionCallbacks = {}
		self._sessions = {}
		self._callbackHandler = _CallbackHandler(self._create_session_from_id)
		self._isStarting = True
		self._startingRequestId = self._idGen.next()
		self._sender({'id': self._startingRequestId, 'op': 'describe'})

	def _create_session_from_id(self, session_id):
		if not session_id in self._sessions:
			self._sessions[session_id] = NREPLSession(self, session_id, self._idGen)
		return self._sessions[session_id]

	def create_new_session(self, newSessionCb):
		'''creates a new session and returns it once it is created with the callback method

		>>> import itertools
		>>> idGenerator = (str(i) for i in itertools.count(1))
		>>> def sender(data):
		...    print data
		>>> def new_session_cb():
		...     pass
		>>> session = SessionContainer(sender, idGenerator)
		>>> session.create_new_session(new_session_cb)
		{'id': '1', 'op': 'clone'}

		:param newSessionCb: callback that will be called with the newly created session object
		:type newSessionCb: function accepting one object, an NreplSession

		'''

		newSessionsId = self._idGen.next()

		self._newSessionLock.acquire();
		self._newSessionCallbacks[newSessionsId] = newSessionCb
		self._newSessionLock.release();

		data = {
			'op': 'clone',
			'id': newSessionsId
		}

		self._sender(data)

	def _handle_new_session_response(self, data, callback):
		'''internally called when data is received that is a result of requesting a new session'''

		if not 'new-session' in data:
			raise ValueErrro('data must contain new-session')

		newSessionId = data['new-session']
		newSession = NREPLSession(self, newSessionId, self._idGen)
		self._sessions[newSessionId] = newSession
		callback(newSession)


	def _accept_data(self, data):
		'''called by the channel when data is received 

		data => python data structure'''

		# if self._isStarting:


		if not 'id' in data:
			raise ValueError('data does not contain an "id" field')

		id_ = data['id']
		if not 'session' in data:
			raise ValueError('data must contain session, data = {0}'.format(data))

		sessionId = data['session']

		if self._sessions.has_key(sessionId):
			self._sessions[sessionId]._receive_results(data)
		else:

			newSessionCallback = None

			self._newSessionLock.acquire()
			if self._newSessionCallbacks.has_key(id_):
				newSessionCallback = self._newSessionCallbacks.pop(id_)
			self._newSessionLock.release()

			if newSessionCallback is None:
				raise KeyError("Unable to find an existing or new session corresponding with this data '{0}'".format(data))
			else:
				self._handle_new_session_response(data, newSessionCallback)

	def _submit(self, data):
		"""Submits data to the channel. Called by the session.

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""

		if not 'session' in data:
			raise ValueError('data must contain session')

		sessionId = data['session']

		if not sessionId in self._sessions:
			raise ValueError('called _submit with data that references a session that was not created with this container')

		self._sender(data)


sessionidCreator = (str(i) for i in itertools.count(1))

tcp_sessions = {}

def stop_bcode_over_tcp_session_container(sessionContainer):
	tcp = tcp_sessions.pop(sessionContainer)
	tcp.stop()

def create_bcode_over_tcp_session_container(host, port):
	'''creates a new session and returns it. Connects with an NREPL that 
	is hosted on host:port and uses bencode as the transport

	:param host: The hostname or address to connect to
	:type host: string
	:param port: the port number to connect to
	:type port: int
	:return: An instance of SessionContainer that will communicate with the networked NREPL
	that is configured to use bencoding.
	:rtype: SessionContainer

	''' 

	tcp = Tcp(host, port)
	bcode = BCodeTransport(tcp.send)
	tcp.add_callback(bcode.receive)
	sessionContainer = SessionContainer(bcode.send, sessionidCreator)
	bcode.add_callback(sessionContainer._accept_data)

	tcp.start()

	tcp_sessions[sessionContainer] = tcp

	return sessionContainer



