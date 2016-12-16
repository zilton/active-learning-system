# -*- coding: utf-8 -*-
from pymongo.cursor import Cursor
from pymongo.connection import Connection
from pymongo.errors import AutoReconnect

from time import sleep 
import sys
		
def reconnect(f):
	''' Wrapper em torno das funções de conexão com o MongoDb que controla reconexão automática '''
	def f_retry(*args, **kwargs):
		wait = 2
		while True:
			try:
				return f(*args, **kwargs)
			except KeyboardInterrupt: 
				raise RuntimeError("Interrompido")
			except:
				print >> sys.stderr, 'Mongo auto reconnect (Inweb): Fail to execute %s [%s]. Waiting %f s' % (f.__name__, sys.exc_info()[0], wait)
				sleep(wait)
	return f_retry

Cursor._Cursor__send_message = reconnect(Cursor._Cursor__send_message)
Connection._send_message = reconnect(Connection._send_message)
Connection._send_message_with_response = reconnect(Connection._send_message_with_response)
