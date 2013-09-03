#! /usr/bin/env python


from bcode_transport import BCodeTransport
from tcp import Tcp

import argparse, sys, bcode, uuid, logging, time, threading

logger = logging.getLogger(__name__)

stopSignal = threading.Event()

def callback(s):
	logger.info("callback with data: '{0}'".format(s))
	stopSignal.set()

if __name__ == '__main__':
	cliParser = argparse.ArgumentParser(description="Mucking around with nrepl")
	cliParser.add_argument("-ll", "--logLevel", help="The logging verbosity", default='DEBUG', choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'])
	cliParser.add_argument("-n", "--hostname", help="The hostname to connect to. Default = 'localhost'", default="localhost")
	cliParser.add_argument("port", type=int, help="The port to connect to")
	args = cliParser.parse_args()

	effectiveLogLevel = getattr(logging, args.logLevel.upper(), None)
	logging.basicConfig(level=effectiveLogLevel)


	tcp = Tcp(args.hostname, args.port)
	bcode = BCodeTransport(tcp.send, callback)
	tcp.add_callback(bcode.receive)
	logger.debug('created new tcp')

	tcp.start()
	logger.debug('started the tcp')

	bcode.send({"op": "describe"})

	stopSignal.wait()
	logger.debug('slept')
	tcp.stop()
	logger.debug('stopped')



	





