#! /usr/bin/env python

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import clientFromString

from asyncbcodedeserialiser import AsyncBCodeDeserialiser

import argparse, sys, bcode, uuid, logging

logger = logging.getLogger(__name__)


class NreplSession:
	def __init__(self, sessionId, protocol):
		self._protocol = protocol
		self._sessionId = sessionId
		self._evalCbs = []

	def registerEvalCallback(self, cb):
		self._evalCbs.append(cb)

	def eval(self, lispCode):
		self._protocol._sendMessage(
			{
				"op": "eval", 
				"session": self._sessionId,
				"code": lispCode
			},
			cb=self.receiveEvalResult)

	def receiveEvalResult(self, evalResult):
		map(lambda f: f(evalResult), self._evalCbs)

	def receiveResult(self, result):
		map(lambda f: f(result), self._evalCbs)


	def close(self):
		messageId = self._protocol._newId()
		self._protocol._sendMessage(
			{
				"op": "close",
				"session": self._sessionId
			},
			messageId=messageId,
			cb=lambda c: self._protocol._sessions.pop(self._sessionId))


class BencodeNREPL(Protocol):


	def __init__(self):
		self._deserialiser = AsyncBCodeDeserialiser()
		self._deserialiser.register_cb(self.nreplDataReceived)
		self._sessions = {}
		self._messageCallbacks = {}


	def _newId(self):
		return uuid.uuid4().hex


	def _sendMessage(self, operation, messageId=None, cb=None):
		if messageId == None:
			messageId = self._newId()
		if cb != None:
			self._messageCallbacks[messageId] = cb
		operation['id'] = messageId
		dataToBeSent = bcode.bencode(operation)
		logger.debug('nrepl --> {0}'.format(operation))
		self.transport.write(dataToBeSent)

	
	def dataReceived(self, str):
		self._deserialiser.push_data(str)

	
	def nreplDataReceived(self, data):
		logger.debug('nrepl <-- {0}'.format(data))
		
		if 'id' in data:
			messageId = data['id']
			if messageId in self._messageCallbacks:
				cb = self._messageCallbacks[messageId]
				cb(data)
				if 'status' in data:
					statii = set(data['status'])
					if 'done' in statii:
						self._messageCallbacks.pop(messageId)

		elif 'session' in data:
			sessionId = data['session']
			if sessionId in self._sessions:
				self._sessions[sessionId].receiveResult(data)

		else:
			logger.warning('Received unexpected data:\n{0}'.format(data))


	def newSession(self):
		result = Deferred()

		def newSessionDataReceived(data):
			sessionId = data['new-session']
			newSession = NreplSession(sessionId, self)
			self._sessions[sessionId] = newSession
			result.callback(newSession)


		self._sendMessage({"op": "clone"}, cb=newSessionDataReceived)
		return result
		

class BencodeNREPLFactory(Factory):
	def buildProtocol(self, addrs):
		return BencodeNREPL()


def gotSession(s):
	logger.info('got the session!')
	s.registerEvalCallback(lambda d: logger.info('got eval {0}'.format(d)))
	s.eval('(+ 3 4)')
	s.close()


def gotProtocol(p):
	session = p.newSession()
	session.addCallback(gotSession)


if __name__ == '__main__':
	cliParser = argparse.ArgumentParser(description="Mucking around with nrepl")
	cliParser.add_argument("-ll", "--logLevel", help="The logging verbosity", default='DEBUG', choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'])
	cliParser.add_argument("-n", "--hostname", help="The hostname to connect to. Default = 'localhost'", default="localhost")
	cliParser.add_argument("port", type=int, help="The port to connect to")
	args = cliParser.parse_args()

	effectiveLogLevel = getattr(logging, args.logLevel.upper(), None)
	logging.basicConfig(level=effectiveLogLevel)
	
	connectionString = 'tcp:host={0}:port={1}'.format(args.hostname, args.port)
	logger.info('connecting to "{0}"'.format(connectionString))
	endPoint = clientFromString(reactor, connectionString);
	d = endPoint.connect(BencodeNREPLFactory())
	d.addCallback(gotProtocol)
	d.addErrback(lambda str: logger.error('{0}'.format(str)))
	reactor.callLater(5, reactor.stop)
	reactor.run()



	





