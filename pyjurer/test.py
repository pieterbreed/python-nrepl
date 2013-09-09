#! /usr/bin/env python


from session_container import *

import argparse, sys, uuid, logging, time, threading

logger = logging.getLogger(__name__)

stopSignal = threading.Event()

def closed(session, result):
	print 'described as: {0}'.format(result)
	stopSignal.set()

def evalcb(session, res):
	print "the answer is: {0}".format(res)
	session.describe(closed)
	# time.sleep(5)

def new_session_callback(s):
	logger.debug('received data, the type is {0}'.format(s.__class__))
	logger.info("callback with data: '{0}'".format(s))
	s.eval("(println (+ 3 4))", evalcb)

if __name__ == '__main__':
	cliParser = argparse.ArgumentParser(description="Mucking around with nrepl")
	cliParser.add_argument("-ll", "--logLevel", help="The logging verbosity", default='DEBUG', choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'])
	cliParser.add_argument("-n", "--hostname", help="The hostname to connect to. Default = 'localhost'", default="localhost")
	cliParser.add_argument("port", type=int, help="The port to connect to")
	args = cliParser.parse_args()

	effectiveLogLevel = getattr(logging, args.logLevel.upper(), None)
	logging.basicConfig(level=effectiveLogLevel)

	sessionContainer = create_bcode_over_tcp_session_container(args.hostname, args.port)
	logger.debug('created new tcp')
	session = sessionContainer.create_new_session(new_session_callback)

	stopSignal.wait()
	logger.debug('slept')
	stop_bcode_over_tcp_session_container(sessionContainer)
	logger.debug('stopped')



	





