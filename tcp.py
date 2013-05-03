# /usr/bin/env python

import unittest, thread

TCP_CHANNEL_TIMEOUT = 1 # seconds, float value
TCP_READ_BUFFER_SIZE = 4098

def socketThreadMain(socket, sendQueue, receiveQueue, stoppedEvent):
	'''this method will perform the communications with a socket-like object
	and perform sending and receiving of data via the passed Queues.

	socket => an object supporting send(byte[]) : int, recv(int) : byte[] & close()

	sendQueue => a Queue object with which this thread is controlled

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

	receiveQueue => a queue containing raw bytes/string read from the socket

	stoppedEvent => an Event that signals when the thread has terminated

	'''

	mustStop = False
	received = ''
	while not mustStop:

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
						sent = socket.send(messageContents)
						messageContents = messageContents[sent:]
			except Queue.Empty, e:
				hasStuffToSend = False

		# if we don't have anything else to send
		# and we did not get a request to stop then 
		# lets try reading for a while
		if not mustStop:
			moreToRead = True
			# try to read everything from the socket
			# that we can read now without waiting to long for
			while moreToRead:
				try:
					received = received + socket.recv(TCP_READ_BUFFER_SIZE)
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


	socket.close()
	stoppedEvent.set()

class Tcp:
	'''provides an abstraction over a tcp/ip connection'''

	def __init__(self, host, port):
		'''creates a new TcpChannel which can send and receive data
		to and from a tcp/ip socket.

		host => the hostname or address to connect to
		port => the port number to connect to on host'''

		self._socketSendQueue = Queue.Queue()
		self._socketReceiveQueue§ = Queue.Queue()
		self._stoppedEvent = thread.Event()
		self._stoppedEvent.clear()
		thread.start_new_thread(socketThreadMain, host, port, self._socketSendQueue, self._socketReceiveQueue, self._stoppedEvent)

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

	def receive(self):
		'''this is a synchronized method (can only be called on one thread at a time) and reads 
		everything from the sockets received queue and returns it to the caller'''
		self._processReceivesLock.acquire()
		received = ''
		while not self._socketReceiveQueue.empty():
			try:
				received = received + self._socketReceiveQueue.qet_nowait()
			except Queue.Empty:
				pass
		self._processReceivesLock.release()
		return received

class MockSocket:

	def __init__(self, recvs):
		'''recvs => list of items. items must be either strings or the value True.
		When True is read, a Queue.Empty will be raised

		sends => similarly a list of items. items must be strings or the Value True.
		When True is encountered, a Queue.Empty is raised'''
		self._recvs = recvs
		self._sends = []
		self._closeCalled = False


	def send(self, bs):
		self._sends.append(bs)

	def recv(self, i):
		res = self._recvs.pop()
		return res

	def close(self):
		self._closeCalled = True

class MockQueue:

	def __init__(self, gets, putsAllows):
		'''gets => a list of things that will be read. Must be either a None or 
		python item. For every None a Queue.Empty will be raised

		putsAllows => an item corresponding to every puts invocation. True
		accepts the put and False raises an Queue.Full'''
		self._gets = gets
		self._puts = []
		self._putsAllows = putsAllows

	def get_nowait(self):
		return self._gets.pop()

	def put_nowait(self, received):
		allow = self._putsAllows.pop()
		if allow:
			self._puts.append(received)
		else
			raise Queue.Full


class TcpTests(unittest.TestCase):
	def test_thread_read_1():
		socketReceives = ['aoeu']
		socket = MockSocket(socketReceives)

		sendQueue = MockQueue([False, {'type': 'control', 'op': 'stop'}], None)
		receiveQueue = MockQueue(None, [True])
		
		stoppedEvent = thread.Event()

		socketThreadMain(socket, sendQueue, receiveQueue, stoppedEvent)

		self.assertTrue(stoppedEvent.is_set())
















