#! /usr/bin/env python
# base interface for channel

import socket, Queue

class Channel(object):
	def submit(self, data, session):
		"""Submits data to the channel.

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""


		raise NotImplementedError()

TCP_CHANNEL_TIMEOUT = 1 # seconds, float value
TCP_READ_BUFFER_SIZE = 4098

def socketThreadMain(host, port, sendQueue, receiveQueue, stoppedEvent):
	'''this method will perform the communications with (host, port)
	and perform sending and receiving of data via the passed Queues.
	SendQueue expects dicts for instructions:

	two types are supported: 
	Control message, deals with the state of the thread
	{
		"type": "control",
		"op": "stop" # only one supported
	}

	Messaging message, instructs the thread to send a message on the socket:
	{
		"type": "message",
		"contents": string/bytes to be sent
	}

	receiveQueue contains raw bytes/string read from the socket

	'''

	s = socket.create_connection((host, port), TCP_CHANNEL_TIMEOUT)

	mustStop = False
	received = ''
	while !mustStop:

		# sends everything that is in the send queue first
		hasStuffToSend = True
		while hasStuffToSend:
			try:
				stuffToSend = sendQueue.get_nowait() # raises Queue.Empty if there is nothing to read

				if stuffToSend['type'] == 'control':
					if stuffToSend['op'] == 'stop':
						mustStop = True
						break
				elif stufftoSend['type'] == 'message':
					messageContents = stufftoSend['contens']
					while len(messageContents) > 0:
						sent = s.send(messageContents)
						messageContents = messageContents[sent:]
			except Queue.Empty, e:
				hasStuffToSend = False

		# if we don't have anything else to send
		# and we did not get a request to stop then 
		# lets try reading for a while
		if !mustStop:
			moreToRead = True
			# try to read everything from the socket
			# that we can read now without waiting to long for
			while moreToRead:
				try:
					received = received + s.recv(TCP_READ_BUFFER_SIZE)
				except socket.timeout:
					moreToRead = False

			# we've received everything that we can right now
			# let's try sending it back
			try:
				receiveQueue.put_nowait(received)
				received = ''
			except Queue.Full:
				# we can't send it back right now because the queue is full
				# we're not doing anything with this
				# since we can just put it next time round
				pass


	s.shutdown()
	s.close()
	stoppedEvent.set()

class TcpChannel(Channel):
	'''provides a channel over a tcp/ip connection'''

	def __init__(self, host, port, receivedDataCb):
		'''creates a new TcpChannel which can send and receive data
		to and from a tcp/ip socket.

		host => the hostname or address to connect to
		port => the port number to connect to on host
		receivedDataCb => a callback that will be called with one argument,
			the received data, on the same thread as processReceives are called'''

		self._socketSendQueue = Queue.Queue()
		self._socketReceiveQueue§ = Queue.Queue()
		self._stoppedEvent = thread.Event()
		self._stoppedEvent.clear()
		thread.start_new_thread(socketThreadMain, host, port, self._socketSendQueue, self._socketReceiveQueue, self._stoppedEvent)

		self._cb = receivedDataCb
		self._processReceivesLock = thread.Lock()

	def stop(self):
		'''stops the tcp thread and the socket and waits for it to clean itself up'''
		self._socketSendQueue.put(
			{
				'type': 'control', 
				'op': 'stop'
			})
		self._stoppedEvent.wait()

	def send(self, data, session):
		self._sessions.add(session)
		self._socketSendQueue.put(
			{
				'type': 'message',
				'contents': data
			})

	def processReceives(self):
		'''this is a synchronized method (can only be called on one thread at a time) and reads 
		everything from the sockets received queue and calls the callback on the same thread
		as this method was called from'''
		self._processReceivesLock.acquire()
		received = ''
		while !self._socketReceiveQueue.empty():
			try:
				received = received + self._socketReceiveQueue.qet_nowait()
			except Queue.Empty:
				pass
		self._processReceivesLock.release()
		self._cb(received)















