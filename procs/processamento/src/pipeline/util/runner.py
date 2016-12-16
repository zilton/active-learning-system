# -*- coding: utf-8 -*-
from pika.spec import BasicProperties
from pipeline.base_filter import configure_filter_logging, BaseFilter
from pipeline.em_import_filter import EmImportFilter
from pipeline.entity_filter import EntityFilter
from pipeline.geo_filter import GeoFilter
from pipeline.lac import LacSocketCommunicator
from pipeline.lac_classifier_filter import LacClassifierFilter
from pipeline.language_filter import LanguageFilter
from pipeline.map_filter import MapFilter
from pipeline.reader_filter import ReaderFilter, EXCHANGE_NAME
from pipeline.rules_filter import RulesFilter
from pipeline.terms_filter import TermFilter
from pipeline.unload_filter import UnloadFilter
from pipeline.updater_filter import UpdaterFilter
from pipeline.url_expander_filter import UrlExpanderFilter
from pipeline.util.load_workflow import WorkflowLoader
from pipeline.util.mqmock import RabbitConnectionMock, MethodMock
import simplejson
import sys
from pipeline.index_filter import IndexFilter
#from pipeline.index_filter import IndexFilter
#from pipeline.sort_to_followers_filter import SortToFollowersFilter
#import gevent
logger = configure_filter_logging('pipeline.runner')

def _get_filters(workflow, lac, lac_classification, mock_conn):
	filters = {	'reader': ReaderFilter(workflow, mock_conn),
				'lang': LanguageFilter(workflow, mock_conn), 
				'term': TermFilter(workflow, mock_conn), 
				'unload': UnloadFilter(workflow, mock_conn), 
				'rule': RulesFilter(workflow, mock_conn), 
				'entity': EntityFilter(workflow, lac, mock_conn), 
				'url': UrlExpanderFilter(workflow, mock_conn), 
				'update': UpdaterFilter(workflow, mock_conn), 
				'index': IndexFilter(workflow, mock_conn), 
				'lac_classifier': LacClassifierFilter(workflow, lac_classification, mock_conn), 
				'geo': GeoFilter(workflow, mock_conn), 
				'map': MapFilter(workflow, mock_conn), 
				#'followers': SortToFollowersFilter(workflow, mock_conn),
				'followers': None, 
				'friends': None, 
				'em_import': EmImportFilter(workflow, mock_conn),
				'followers_high_priority': None, 
				'followers_medium_priority': None, 
				'followers_low_priority': None
	};
	return filters

class FileInputWorkflowRunner():
	''' 
	Executa o workflow usando como entrada um arquivo (um objeto JSON por linha) no sistema de arquivos.
	Toda troca de mensagens é feita na memória RAM, ao invés de usar um servidor de filas. 
	Útil quando se quer processar grandes volumes de dados a partir de arquivos. 
	Note que neste caso, o ideal é processar cada arquivo separadamente, com uma instância
	deste programa lendo 1 arquivo e todas rodando em paralelo. 
	'''
	def __init__(self, filename, workflow, collection):
		self.filename = filename
		self.workflow = workflow
		self.collection = collection
		self.mock_queue = RabbitConnectionMock()
		
	def process(self):
		
		lac_server, lac_port = workflow['global']['lac-server']
		lac = LacSocketCommunicator(lac_server, lac_port)
		
		lac_server, lac_port = workflow['global']['lac-classification-server']
		lac_classification = LacSocketCommunicator(lac_server, lac_port)
		
		filters = _get_filters(workflow, lac, lac_classification, self.mock_queue)
		
		reader = ReaderFilter(self.workflow, self.mock_queue)
		
		channel = self.mock_queue.channel()
		method = MethodMock("queue", "")
		for i, _ in enumerate(reader.read_input(self.filename, self.collection, lazy=True)):
			while True:
				queues = channel.exchanges[EXCHANGE_NAME]
				names = queues.keys()
				for name in names:
					method.routing_key = name
					for body in queues[name]:
						obj = simplejson.loads(body)
						print "Item %d (%d), " % (i, obj['_id']),
						for target in name[4:].split('.'):
							f = filters.get(target)
							if f:
								print target,
								f.callback(channel, method, {}, body)
						print 
								
					del queues[name]
				if len(names) == 0:
					break
			#while True
		#while result
class RabbitMQWorkflowRunner():
	'''
	Processa todo o workflow em um processo, mas permite que existam vários processos simultâneos lendo do RabbitMQ.
	Alguns estágios irão requerer concentrar os documentos para análise em conjunto.
	'''
	def __init__(self, workflow, queue_name="reader"):
		self.workflow = workflow
		self.queue_name = queue_name
		self.mock_connection = RabbitConnectionMock()
		self.mock_channel = self.mock_connection.channel()
		self.mock_channel.exchange_declare(EXCHANGE_NAME, 'topic', True)
		
		server, vhost, user, passwd = workflow['global']['rabbitmq']
		self.rabbit_conn = BaseFilter.connect_to_mq(server, vhost, user, passwd)
		
		lac_server, lac_port = workflow['global']['lac-server']
		self.lac = LacSocketCommunicator(lac_server, lac_port)
		
		lac_server, lac_port = workflow['global']['lac-classification-server']
		self.lac_classification = LacSocketCommunicator(lac_server, lac_port)
		
		self.filters = _get_filters(workflow, self.lac, self.lac_classification, self.mock_connection)
		self.counter = 0
		
		#Monkey patching: evitar codificar e decodificar objeto desnecessariamente
		BaseFilter.decode = lambda s, data, parse_dates=False: data
		BaseFilter.encode = lambda s, obj: obj
		self.counter = 0
		
	def process(self):
		
		self.channel = self.rabbit_conn.channel()
		self.channel.exchange_declare(exchange=EXCHANGE_NAME, type='topic', durable=True)
		result = self.channel.queue_declare(queue=self.queue_name, durable=True, exclusive=False)
		self.queue_name = result.method.queue
		self.channel.queue_bind(exchange=EXCHANGE_NAME, queue=self.queue_name, routing_key='#.{}.#'.format(self.queue_name))
		self.channel.basic_consume(self.callback, queue=self.queue_name, no_ack=False)
		self.channel.start_consuming()
		
	
	def publish(self, exchange, routing_key, body, durable=False):
		if durable:
			properties = BasicProperties( delivery_mode = 2) # make message persistent
		else:
			properties = None
		self.channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body, properties=properties)
		
	def callback(self, channel, method, properties, original_body):	
		
		mock_method = MethodMock("", method.routing_key)
		
		obj = simplejson.loads(original_body)
		contexto =  obj['_tmp_']['context']
		#print obj['_id']
		if self.counter % 1000 == 0:
			logger.info("Processados %s documentos (%s)", self.counter, obj['_id'])
		self.filters[self.queue_name].callback(self.mock_channel, mock_method, {}, obj)
		#print obj['text']
		self.counter += 1
		while True:
			# A cada momento, novas filas podem ser criadas no exchange, por isto tem que ler a cada iteração.
			queues = self.mock_channel.exchanges[EXCHANGE_NAME]
			names = queues.keys()
			print names
			for name in names:
				method.routing_key = name
				for body in queues[name]:
					for target in name.split('.'):
						if target in ('em_import', 'trends', 'url', 'map'):
							self.publish(EXCHANGE_NAME, '{}.{}'.format(contexto, target), simplejson.dumps(body), True)
						else:
							if not target.isdigit(): 
								#raw_input("Processando {}\n >".format(target))
								f = self.filters.get(target) #Melhorar, porque testa outros campos inutilmente, como o id do contexto
								if f:
									#logger.info("Processando fila %s", target)
									result = f.callback(self.mock_channel, method, {}, body),
									if result is None or result[0] is None:
										self.publish(EXCHANGE_NAME, '{}.{}'.format(contexto, target), simplejson.dumps(body), True)
										logger.error(u"Erro executando %s: nenhum resultado retornado. Verifique os logs. Documento será gravado na fila novamente.", target)
									#else:
									#	print result
								else:
									logger.error(u"Target desconhecido: %s", target)
				del queues[name]
			if len(names) == 0:
				break
		#while True
		channel.basic_ack(delivery_tag = method.delivery_tag)
		#raw_input("Pressione ENTER \n> ")
if __name__ == '__main__':
	if len(sys.argv) != 3 or sys.argv[1] != '-w':
		print >> sys.stderr, u"Parâmetro ausente: -w <workflow_file>"
		sys.exit(1)	
	workflow = WorkflowLoader().load(sys.argv[2])
	#print workflow['6']['rule']['itemsets']
	runner = RabbitMQWorkflowRunner(workflow, 'lang')
	runner.process()
