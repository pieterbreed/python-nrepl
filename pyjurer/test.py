#! /usr/bin/env python

from __future__ import print_function

from session_container import *

import argparse, sys, uuid, logging, time, threading
from channels.tcp import Tcp
from transports.bcode_transport import BCodeTransport
from callback_handler import _CallbackHandler

logger = logging.getLogger(__name__)

stopSignal = threading.Event()

def value(session, id_, res):
	print("the answer is: {0}".format(res))
	# time.sleep(5)

def stdout(session, id_, out):
	print(">>> {0}".format(out))

def stdin(session, id_):
	logger.debug('stdin called')
	session.stdin('hey man\n')

def done(session, id_):
	stopSignal.set()

def sessions(session, id_, sessions):
	logger.debug('hier')
	print( "sessions: {0}".format(sessions))
	#session.eval('(read-line)', value=value, stdout=value, stdin=stdin, done=done)

def new_session_callback(s):
	logger.debug('received data, the type is {0}'.format(s.__class__))
	logger.info("callback with data: '{0}'".format(s))
	s.ls_sessions(sessions=sessions, done=done)


if __name__ == '__main__':
	cliParser = argparse.ArgumentParser(description="Mucking around with nrepl")
	cliParser.add_argument("-ll", "--logLevel", help="The logging verbosity", default='DEBUG', choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'])
	cliParser.add_argument("-n", "--hostname", help="The hostname to connect to. Default = 'localhost'", default="localhost")
	cliParser.add_argument("port", type=int, help="The port to connect to")
	args = cliParser.parse_args()

	effectiveLogLevel = getattr(logging, args.logLevel.upper(), None)
	logging.basicConfig(level=effectiveLogLevel)

	def sessionFactory(id_):
		logger.debug('session factory called, returning string')
		return "" + id_

	def initialCallback(session, data):
		logger.debug('initial callback with session {0} and data {1}'.format(session, data))
		stopSignal.set()

	cb = _CallbackHandler(sessionFactory, initialCallback)

	tcp = Tcp('localhost', 58791)
	bcode = BCodeTransport(tcp.send)
	tcp.add_callback(bcode.receive)
	bcode.send({'op': 'describe', 'id':1})
	tcp.start()
	bcode.add_callback(cb.accept_data)


	# sessionContainer = create_bcode_over_tcp_session_container(args.hostname, args.port)
	# logger.debug('created new tcp')
	# session = sessionContainer.create_new_session(new_session_callback)

	stopSignal.wait()
	# logger.debug('slept')
	# stop_bcode_over_tcp_session_container(sessionContainer)
	# logger.debug('stopped')



	





