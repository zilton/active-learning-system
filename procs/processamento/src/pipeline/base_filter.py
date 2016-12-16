# -*- coding: utf-8 -*-
from ConfigParser import NoSectionError
import datetime
from email.utils import parsedate
import functools
import logging.config
from multiprocessing import Process
from optparse import OptionParser
import os
from random import shuffle
import re
import signal
import string
import sys
import time
import traceback
import unicodedata
import urlparse

from pika import BlockingConnection, ConnectionParameters, BasicProperties, PlainCredentials
from pika.adapters.select_connection import SelectConnection
import pymongo
import simplejson

from pipeline.util.load_workflow import WorkflowLoader
import requests
from pymongo import MongoClient

# import beanstalkc
try:
	import nsq
except ImportError:
	pass
try:
	import psutil
	import memcache
except ImportError:
	pass

def define_common_parameters(parser):
	''' 
	Define os parâmetros comuns que estão disponíveis na execução de todos os filtros
	'''
	parser.add_option("-w", "--workflow", dest="workflow", help=u"Workflow a ser cumprido", metavar="WORKFLOW")
	parser.add_option("-n", "--instances", dest="instances", metavar="INSTANCES", default="1",
					help=u"Número de instâncias do processo que serão executadas. Padrão = 1")
	parser.add_option("", "--pidfile", dest="pidfile", 
					help=u"Caminho completo do arquivo onde registra o pid do processo pai", metavar="PIDFILE")

def configure_filter_logging(logger_name=None):
	config_file = os.path.join(os.path.dirname(__file__), 'logging.conf')
	try:
		logging.config.fileConfig(config_file)
	except NoSectionError:
		logging.warn(u'Arquivo de configuração (%s) não encontrado. Usando configurações padrão.', config_file)
	if logger_name:
		return logging.getLogger(logger_name)
		
def sigterm_handler_main(pids):
	def sigterm_handler(signal, frame):
		print 'You killed me!'
		for p in pids:
			os.kill(p.pid,9)
		os.sys.exit(0)
	return sigterm_handler

def main_routine_filter(filter_name, run_callback, extra_params_callback=None):
	
	parser = OptionParser()
	define_common_parameters(parser)

	parser.add_option("-j", "--project", dest="project_name", help=u"Project" , metavar="PROJECT_NAME")
	parser.add_option("-t", "--host", dest="host", help=u"Host" , metavar="HOST")
	parser.add_option("-b", "--db", dest="db", help=u"Database" , metavar="DB")
	parser.add_option("-z", "--port", dest="port", help=u"Port to connect" , metavar="PORT")
	
	(options, _) = parser.parse_args()
	#start_filter(int(options.instances), workflow, options.pidfile, run_callback, args=args)
	if options.project_name and options.host and options.db:
		if not options.port:
			port = 27017
		else:
			port = options.port
		mongoCon = MongoClient(host=options.host, port=port)
		db = getattr(mongoCon, options.db)
		project = db['project'].find_one({"name":options.project_name})

		if project:
			workflow = WorkflowLoader().load(dict(project['workflow']))
			server, vhost, user, passwd = [str(x) for x in workflow['global']['rabbitmq']]
			conn = BaseFilter.connect_to_mq(server, vhost, user, passwd)
			args = [workflow, project, server, vhost, user, passwd]
			start_filter(int(options.instances), workflow, project, options.pidfile, run_callback, args=args)
	else:
		parser.print_usage()


def start_filter(instances, workflow, project, pidfile, run_callback, args):
	'''
	Inicia a execução do filtro
	'''
	if pidfile: #Registra o PID para que se for necessário, possa ser usado o comando kill para interromper o programa
		with open(pidfile, 'w') as f:
			print >> f, os.getpid()
	
	#Se apenas uma instância, não usa multiprocess (facilita depuração no Eclipse)
	if int(instances) == 1:
		run_callback(*args)
	else:
		processes = []
		for _ in xrange(0, int(instances)):
			p = Process(target=run_callback, args=args)
			processes.append(p)
			p.daemon = True
			p.start()
		signal.signal(signal.SIGTERM, sigterm_handler_main(processes))
		for p in processes:
			try:
				p.join()
			except KeyboardInterrupt:
				pass
			
class JSONDateTimeEncoder(simplejson.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, (datetime.date, datetime.datetime)):
			return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')
		else:
			return simplejson.JSONEncoder.default(self, obj)

def datetime_decoder(d):
	if isinstance(d, list):
		pairs = enumerate(d)
	elif isinstance(d, dict):
		pairs = d.items()
	result = []
	for k,v in pairs:
		if isinstance(v, basestring):
			try:
				# The %f format code is only supported in Python >= 2.6.
				# For Python <= 2.5 strip off microseconds
				# v = datetime.datetime.strptime(v.rsplit('.', 1)[0],
				#	 '%Y-%m-%dT%H:%M:%S')
				v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%f')
			except TypeError:
				pass
			except ValueError:
				try:
					v = datetime.datetime.strptime(v, '%Y-%m-%d').date()
				except ValueError:
					pass
		elif isinstance(v, (dict, list)):
			v = datetime_decoder(v)
		result.append((k, v))
	if isinstance(d, list):
		return [x[1] for x in result]
	elif isinstance(d, dict):
		return dict(result)
EXPR_SPACE_REPETITION = re.compile(r'(\s)\1{1,}')

class QueueStrategy:
	contexto = None
	def set_contexto(self, ctx):
		self.contexto = ctx
		
class RabbitMQStrategy(QueueStrategy):
	'''
	Usa o RabbitMQ como servidor de mensagens (fila) no processamento
	'''
	def __init__(self, conn=None):

		self.connection = conn
		self.out_channels_exchange = {}
		self.out_channels = {}
		self.queue_name = None
		self.fetch_opts = {}
		self.mq = 'rabbitmq'
		
	def publish(self, exchange, routing_key, body, durable=False, ttl=0):
		''' 
		Envia mensagem para servidor. 
		'''
		channel = self.out_channels_exchange.get(exchange, None)
		if channel is None:
			channel = self.connection.channel()
			channel.exchange_declare(exchange = exchange, type='topic', durable=durable)
			self.out_channels_exchange[exchange] = channel #mantem cache

		params = {}
		if durable:
			params['delivery_mode'] = 2 # make message persistent
		if ttl:
			params['expiration'] = str(ttl)
		if params:
			properties = BasicProperties(**params)
		else:
			properties = None
		channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body, properties=properties)
	
	def consume(self, exchange, routing_key, callback, durable=False, ack=False, queue=None):
		'''
		Inicia o consumo de mensagens do servidor. A mensagem será recebida por <code>callback</code>.
		'''
		channel = self.out_channels_exchange.get(exchange, None)
		if channel is None:
			channel = self.connection.channel()
			channel.queue_declare(queue=queue, durable=durable)
			self.out_channels_exchange[exchange] = channel #Mantem cache
		channel.exchange_declare(exchange=exchange, type='topic', durable=durable)
		result = channel.queue_declare(queue=queue, durable=durable, exclusive=False)
		
		self.queue_name = result.method.queue

		channel.queue_bind(exchange=exchange, queue=self.queue_name, routing_key=routing_key)
		if self.fetch_opts.has_key(exchange):
			size, _ = self.fetch_opts[exchange]
			channel.basic_qos(prefetch_count=size)
		
		channel.basic_consume(callback, queue=self.queue_name, no_ack=not ack)
		channel.start_consuming()
		
	def close(self):
		self.connection.close()
	def set_backpressure_multiplier(self, v):
		self.connection.set_backpressure_multiplier(1)
	def add_backpressure_callback(self, back_pressure):
		self.connection.add_backpressure_callback(back_pressure)
	def define_fetch_size(self, exchange, size, count):
		self.fetch_opts[exchange] = (size, count)
	def get_memory_usage(self):
		'''
		Recupera o uso de memória do processo
		'''
		for proc in psutil.process_iter():
			if 'beam.smp' == proc.name:
				p = psutil.Process(proc.pid)
				mem = p.get_memory_info().rss/(1024*1024)
				return mem

				
class MemcacheStrategy(QueueStrategy):
	'''
	Usa algum servidor compatível com o protocolo memcache (kestrel ou darmer) 
	como servidor de mensagens (fila) no processamento
	'''
	def __init__(self, conn=None):

		self.connection = conn
		#self.out_channels_exchange = {}
		#self.out_channels = {}
		self.queue_name = None
		#self.fetch_opts = {}
		self.mq = 'darner'
	
	class Method:
		def __init__(self, routing_key, delivery_tag):
			self.routing_key = routing_key
			self.delivery_tag = delivery_tag
	class Channel:
		def __init__(self):
			self.ack = False
		def basic_ack(self, delivery_tag):
			self.ack = True
			
	def publish(self, exchange, routing_key, body, durable=False, ttl=0):
		''' 
		Envia mensagem para servidor. Considera que cada parte de routing_key, separada por ponto-final, é um destino, 
		exceto se for inteiro (legado: era o id do contexto).
		'''
		for queue in [x for x in routing_key.split('.') if not x.isdigit()]:
			#Note que memcache requer que seja enviado str e não unicode (erro memcache.MemcachedStringEncodingError)
			if not self.connection.set(queue.encode('utf8'), body):
				raise memcache._ConnectionDeadError 
	
	def consume(self, exchange, routing_key, callback, durable=False, ack=False, queue=None):
		'''
		Inicia o consumo de mensagens do servidor. A mensagem será recebida por <code>callback</code>.
		'''
		counter = 0
		channel = MemcacheStrategy.Channel()
		queues = [x for x in routing_key.split('.') if x != '#']
		try:
			while 1:
				for queue in queues:
					if channel.ack:
						cmd = '{}/t={}/close/open'
					else:
						cmd = '{}/t={}/open'
					body = self.connection.get(cmd.format(queue, 5000)) #Aguarda até 5 segundos
					channel.ack = False
					if body:
						callback(channel, MemcacheStrategy.Method(routing_key, counter), None, body)
						counter += 1
		except KeyboardInterrupt:
			self.close()
			raise
	def close(self):
		self.connection.disconnect_all()
	def set_backpressure_multiplier(self, v):
		pass
	def add_backpressure_callback(self, back_pressure):
		pass
	def define_fetch_size(self, exchange, size, count):
		pass
	def get_memory_usage(self):
		'''
		Recupera o uso de memória do processo
		'''
		for proc in psutil.process_iter():
			if self.mq == proc.name:
				p = psutil.Process(proc.pid)
				mem = p.get_memory_info().rss/(1024*1024)
				return mem

class BeanstalkdStrategy(QueueStrategy):
	'''
	Usa o Beanstalkd como servidor de mensagens (fila) no processamento
	'''
	def __init__(self, conn=None):

		self.connection = conn
		#self.out_channels_exchange = {}
		#self.out_channels = {}
		self.queue_name = None
		#self.fetch_opts = {}
		self.mq = 'beanstalkd'
		self.job = None
			
	class Method:
		def __init__(self, routing_key, delivery_tag):
			self.routing_key = routing_key
			self.delivery_tag = delivery_tag
	class Channel:
		def __init__(self, job):
			self.job = job
		def basic_ack(self, delivery_tag):
			self.job.delete()
			
	def publish(self, exchange, routing_key, body, durable=False, ttl=0):
		''' 
		Envia mensagem para servidor. Considera que cada parte de routing_key, separada por ponto-final, é um destino, 
		exceto se for inteiro (legado: era o id do contexto).
		'''
		for queue in [x for x in routing_key.split('.') if not x.isdigit()]:
			self.connection.use(queue.encode('utf8'))
			self.connection.put(body)
	
	def consume(self, exchange, routing_key, callback, durable=False, ack=False, queue=None):
		'''
		Inicia o consumo de mensagens do servidor. A mensagem será recebida por <code>callback</code>.
		'''
		counter = 0
		queues = [x for x in routing_key.split('.') if x != '#']
		try:
			while 1:
				for queue in queues:
					self.connection.watch(queue.encode('utf8'))
				self.connection.ignore('default')
				job = self.connection.reserve()
				channel = BeanstalkdStrategy.Channel(job)
				callback(channel, BeanstalkdStrategy.Method(routing_key, counter), None, job.body)
				counter += 1
		except KeyboardInterrupt:
			self.close()
			raise
	def close(self):
		self.connection.close()
	def set_backpressure_multiplier(self, v):
		pass
	def add_backpressure_callback(self, back_pressure):
		pass
	def define_fetch_size(self, exchange, size, count):
		pass
	def get_memory_usage(self):
		'''
		Recupera o uso de memória do processo
		'''
		for proc in psutil.process_iter():
			if self.mq == proc.name:
				p = psutil.Process(proc.pid)
				mem = p.get_memory_info().rss/(1024*1024)
				return mem
class NsqConnection:
	''' Simula uma conexão ao NSQ, pois não há como abrir a conexão no pynsq sem que seja especificado qual a função
		callback.
	'''
	def __init__(self, server, path):
		self.server = server
		self.time_in_secs = 0
		self.path = path
		
	def add_timeout(self, time_in_secs, callback):
		self.time_in_secs = time_in_secs
		self.callback = callback
		nsq.tornado.ioloop.IOLoop.instance().add_timeout(time_in_secs + time.time(), callback)
		
class NsqStrategy(QueueStrategy):
	'''
	Usa o servidor NSQ (http://nsq.io) como servidor de mensagens (fila) no processamento.
	Não usar. Não há como fazer o processamento síncrono. Por exemplo, o filtro Reader precisa ser 
	síncrono e não foi possível identificar como fazer isto sem que seja necessário refatorar toda
	a hierarquia de filtros. A maneira de se fazer o processamento síncrono é usar o cliente HTTP para post,
	mas o NSQ se comporta de forma estranha quando há muitos clientes e mensagens, além do que filtros
	que processam batch têm dado problemas com o ACK 
	'''
	def __init__(self, conn=None):

		self.connection = conn
		#self.write_session = requests.Session()
		self.queue_name = None
		self.mq = 'nsq'
		self.buffered_messages = []
		self.exception = None
		self.counter = 0
		
		self.nsq_running = False
		self.writer = nsq.Writer(['{}:4150'.format(self.connection.server)])
		
	class Method:
		def __init__(self, routing_key, delivery_tag):
			self.routing_key = routing_key
			self.delivery_tag = delivery_tag
			
	class Channel:
		def __init__(self):
			self.ack = False
			self.multiple = False
			
		def basic_ack(self, delivery_tag, multiple=False):
			self.ack = True
			self.multiple = multiple
			
	def publish(self, exchange, routing_key, body, durable=False, ttl=0):
		''' 
		Envia mensagem para servidor. Considera que cada parte de routing_key, separada por ponto-final, é um destino, 
		exceto se for inteiro (legado: era o id do contexto).
		'''
		result = True
		partes = routing_key.split('.')
		for queue in partes[1:]:
			if queue[0] != '#':
				r = self.write_session.post(
					'http://{}:4151/pub?topic={}{}'.format(self.connection.server, queue, self.connection.path), 
					data=body.encode('zlib'), timeout=10,)
				#self.writer.pub('{}{}'.format(queue, self.connection.path), body.encode('zlib'), None)
				#Necessário ler o content por causa do Keep-Alive 
				#ver doc http://docs.python-requests.org/en/latest/user/advanced/#keep-alive
				content = r.content
				if content and r.status_code != 200:
					r.raise_for_status()
		return result
	
		
	def _handler(self, message, routing_key, callback):
		message.enable_async()
		self.buffered_messages.append(message)
		
		self.counter += 1
		channel = NsqStrategy.Channel()
		try:
			callback(channel, NsqStrategy.Method(routing_key, self.counter), None, message.body.decode('zlib'))
		except Exception:
			traceback.print_exc(file=sys.stderr)
			traceback.print_tb(sys.exc_traceback, file=sys.stderr)
			time.sleep(5)
		if channel.ack:
			for m in self.buffered_messages:
				m.finish()
			self.buffered_messages = []
	def consume(self, exchange, routing_key, callback, durable=False, ack=False, queue=None):
		'''
		Inicia o consumo de mensagens do servidor. A mensagem será recebida por <code>callback</code>.
		'''
		nsq.Reader(message_handler=functools.partial(self._handler,routing_key=routing_key, callback=callback), 
				max_in_flight=1000, lookupd_http_addresses=['http://{}:4161'.format(self.connection.server)],
				topic='{}{}'.format(queue, self.connection.path), channel='proc', lookupd_poll_interval=15)
		
		#if hasattr(self.connection, 'time_in_secs') and self.connection.time_in_secs:
			#nsq.tornado.ioloop.add_timeout(self.connection.time_in_secs * 1000, self.connection.callback)  # @UndefinedVariable
			#t.start()
		nsq.run()
		
	def close(self):
		self.connection.disconnect_all()
	def set_backpressure_multiplier(self, v):
		pass
	def add_backpressure_callback(self, back_pressure):
		pass
	def define_fetch_size(self, exchange, size, count):
		pass
	def get_memory_usage(self):
		'''
		Recupera o uso de memória do processo
		'''
		pass
'''
' Classe base para todos os filtros.
'''
class BaseFilter(object):
	'''
	Classe base para todos os demais filtros do pipeline.
	'''
	def __init__(self, filter_name, conn=None, workflow=None):

		if isinstance(conn, NsqConnection):
			self.strategy = NsqStrategy(conn)
		else:
			self.strategy = RabbitMQStrategy(conn)
		#self.strategy = MemcacheStrategy(conn)
# 		self.strategy = BeanstalkdStrategy(conn)
		
		self.dest_expr = re.compile(r'((\d+)\.?.*?)\.%s\.\[(.*?)\]\.?(.+)?' % filter_name) 
		self.filter_name = filter_name
		
		#Expressões regulares para tratar o texto
		self.remove_punctuation = re.compile('[%s]' % string.punctuation)
		#Usado para eliminar caracteres repetidos
		self.remove_repetition =[ re.compile('^([rs])\\1'), re.compile('([rs])\\1$'), 
			re.compile('([^rs])\\1{1,}'), re.compile('([\\S\\s])\\1{2,}')]
		self.remove_extra_space = re.compile(r'\s+')
		self.fetch_opts = {}
		self.workflow = workflow
		if workflow:
			self.compress = workflow.get('global').get('compress') == True
		else:
			self.compress = False
		
	def define_fetch_size(self, exchange, size, count):
		self.strategy.define_fetch_size(exchange, size, count)
	
	def close(self):
		self.strategy.close()
	
	def publish(self, exchange, routing_key, body, durable=False, ttl=0):
		if "#END#" not in routing_key:
			return self.strategy.publish(exchange, routing_key, body, durable, ttl)
		
	def _parse_date(self, date):
		if isinstance(date, datetime.datetime):
			return date
		else:
			#Tenta formato RFC
			try:
				date_parsed = datetime.datetime(*parsedate(date)[:6])
			except:
				date_parsed = None
			if not date_parsed:
				#Tenta formato ISO
				try:
					date_parsed = datetime.datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
				except:
					raise TypeError(u'Data no formato inválido')
			return date_parsed 
	def _get_mongo_connection(self, servers, read_only=False):
		connection = pymongo.Connection(servers)
		if read_only:
			db = connection['admin']
			rs_status = db.command('replSetGetStatus')
			candidates = [m for m in rs_status['members'] if m['stateStr'] == 'SECONDARY']
			
			shuffle(candidates)
			return pymongo.Connection(candidates[0]['name'], slave_okay=True)	
		else:
			return connection
		
	def consume(self, exchange, routing_key, callback, durable=False, ack=False, queue=None):
		self.strategy.consume(exchange, routing_key, callback, durable, ack, queue)
		'''
		try:
		except KeyboardInterrupt:
			raise
		except:
			print "Reiniciando channel"
			raise
			pass
		'''
	def callback(self, ch, method, properties, body):
		pass
	
	def process(self):
		pass
	
	def get_memory_usage(self):
		return self.strategy.get_memory_usage()

	def get_strategy(self):
		return self.strategy.mq
	
	def _fill_version_info(self, version, params):
		params['v'] = version
		params['d'] = int(round(time.time() * 1000))
	
	def _strip_accents(self, s):
		return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))
	
	def _remove_space_repetition(self, s):
		return EXPR_SPACE_REPETITION.sub(r'\1', s)

	def _remove_punctuation(self, s, replace=''):
		exclude = set(string.punctuation)
		return ''.join(map(lambda ch: ch if ch not in exclude else replace, s))
	
	def _remove_repetition(self, s):
		result = s
		for exp in self.remove_repetition:
			result = exp.sub(r'\1', result)
		return result
	def set_compress(self, v):
		self.comrpess = v
	def encode(self, obj):
		result = simplejson.dumps(obj, cls=JSONDateTimeEncoder, separators=(',',':'), encoding='utf8')
		if self.compress:
			result = result.encode('zlib')
		return result
	def decode(self, data, parse_dates=False):
		if self.compress:
			data = data.decode('zlib')
		if parse_dates:
			result = simplejson.loads(data, object_hook=datetime_decoder, encoding='utf8')
		else:
			result = simplejson.loads(data, encoding='utf8')
		return result
	@staticmethod
	def connect_to_mq(server, vhost, user, passwd, ioloop=False, on_open_callback=None):

		partes = urlparse.urlparse(server)
			
		result = None
		
		if partes.scheme == '' or partes.scheme == 'rabbitmq': #Legado, usando RabbitMQ
			server = partes.netloc or partes.path
			cred = PlainCredentials(user, passwd)
			if not ioloop:
				result = BlockingConnection(ConnectionParameters(str(server), virtual_host=vhost, credentials=cred))
			else:
				result =  SelectConnection(ConnectionParameters(str(server), virtual_host=vhost, credentials=cred), 
									on_open_callback)
		elif partes.scheme == 'nsq':
			result = NsqConnection(partes.netloc, vhost[1:] if len(vhost) > 1 else '')
		
		return result 
			
# 		Beanstalkd:
# 		(host, port) = server.split(':')
# 		return beanstalkc.Connection(host=host, port = int(port))

# 		Memcached:
		#return memcache.Client([server], socket_timeout=3600*1000) #Valor longo para timeout
	
	def set_backpressure_multiplier(self, v):
		self.strategy.set_backpressure_multiplier(v)

	def add_backpressure_callback(self, back_pressure):
		self.strategy.add_backpressure_callback(back_pressure)
	
	def get_contexto(self, method, obj):
		if '_tmp_' in obj and 'context' in obj['_tmp_']:
			return str(obj['_tmp_']['context'])
		else:
			return method.routing_key.split('.')[0]
		
if __name__ == '__main__':
	BaseFilter().process()
