#! /usr/bin/env python


from asyncbcodedeserialiser import AsyncBCodeDeserialiser
from tcp import Tcp

import argparse, sys, bcode, uuid, logging, time

logger = logging.getLogger(__name__)

if __name__ == '__main__':
	cliParser = argparse.ArgumentParser(description="Mucking around with nrepl")
	cliParser.add_argument("-ll", "--logLevel", help="The logging verbosity", default='DEBUG', choices=['DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'])
	cliParser.add_argument("-n", "--hostname", help="The hostname to connect to. Default = 'localhost'", default="localhost")
	cliParser.add_argument("port", type=int, help="The port to connect to")
	args = cliParser.parse_args()

	effectiveLogLevel = getattr(logging, args.logLevel.upper(), None)
	logging.basicConfig(level=effectiveLogLevel)

	tcp = Tcp(args.hostname, args.port)	
	logger.debug('created new tcp')
	time.sleep(1)
	logger.debug('slept')
	tcp.stop()
	logger.debug('stopped')



	





