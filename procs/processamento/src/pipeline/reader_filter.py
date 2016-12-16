# -*- coding: utf-8 -*-
#
# Lê dados e disponibiza-os para o processamento no pipeline do Observatório da Web.
# Autor: Walter dos Santos Filho <walter@dcc.ufmg.br>
# Versão 3: Suporte a leitura de dados diretamente da fila.
# Versão 2: Controle de back pressure e novo workflow.
# Versão 1: Implementação
#
import datetime
from optparse import OptionParser
import pymongo
import pytz
import re
import simplejson
import sys
import time
import urllib2
from pymongo import MongoClient
import email.utils as eut
from pipeline.base_filter import BaseFilter, configure_filter_logging, define_common_parameters, start_filter, main_routine_filter
from pipeline.util.filters import dict_find
from pipeline.util.load_workflow import WorkflowLoader


FILTERS = {'reader': 'reader', 'classifier': 'classifier', 'update': 'update', 'select_instance': 'select_instance', 'lang':'lang'}

#project = None

EXCHANGE_NAME = 'workflow-1.0'
VERSION=3
OPCAO_SORT = {'TW': '_id',
			  'FB': 'updated_time',
			  'FR': '_id'}

PARTICAO_CHAVE= {'TW': lambda x, y: int((x + y)*.5), 
				 'FB': lambda x, y: x - (x-y)/2}

LOWER = {'TW': 0,
		 'FB': datetime.datetime.strptime('2011-01-01', '%Y-%m-%d')}

TEXT = {'tweets': ['text'],
		'facebook': ['description', 'message', 'name', 'caption'],
		'youtube': ['title', 'description'],
		'forum':['text']}

DATE_FIELD = {'tweets': 'created_at',
			  'facebook': 'created_time',
			  'instagram': 'created_time',
			  'youtube': 'published',
			  'forum': 'created_at',
			  'news': 'published'}

logger = configure_filter_logging(__file__)

class ReaderFilter(BaseFilter):
	''' Lê e adiciona ao pipeline os documentos publicados na última hora '''
	def __init__(self, workflow, project, conn=None):
	
		self.workflow = workflow
		self.project = project
		super(ReaderFilter, self).__init__('reader', conn, workflow=workflow)
		self.sleep_time = 0
		self.counter = 0

	def publish_doc(self, doc, tipo, contexto, collection_name, upsert=False):
		
		#Define valores constantes para o contexto, caso haja algum.
		if self.workflow[contexto]['reader'].has_key('$set'):
			for k, v in self.workflow[contexto]['reader']['$set'].items():
				if doc.has_key(k):
					doc[k].update(v)
				else:
					doc[k] = v
			
		doc['_tmp_'] = {'type': tipo, 'ns': collection_name, 'context': contexto, 'upsert': upsert}
		if '_id' not in doc:
			doc['_id'] = doc.get('id') # Força chave do mongo
		#Formata a data
		doc[DATE_FIELD[tipo]] = self._parse_date(doc[DATE_FIELD[tipo]])
		
		text_fragment = []
		if tipo == 'facebook' or tipo == 'youtube':
			for frag in TEXT[tipo]:
				if doc.has_key(frag):
					text_fragment.append(doc[frag])
			doc['_tmp_']['text_full'] = u" ".join(text_fragment).replace('\\/', '/').replace('"', '')
			
		elif tipo in ('tweets', 'instagram'):
			doc['_tmp_']['text_full'] = doc['text'].replace('\\/', '/')
		elif tipo == 'forum':
			doc['_tmp_']['text_full'] = doc['text'].replace('\\/', '/')#.encode('ascii', 'ignore') 
		else:
			raise Exception(u"Tipo de dado desconhecido: %s" % tipo)
		#marcacao da versao e operacao
		params = {}
		self._fill_version_info(VERSION, params)
		if doc.has_key('control'):
			doc['control'].update({'last': 'READ', 'read': params})
		else:
			doc['control'] = {'last': 'READ', 'read': params}
			
		doc['control']['project'] = self.project['name']

		try:
			contexto_info = self.workflow.get(contexto).get('reader')
			doc_type_info = contexto_info = contexto_info.get(tipo, contexto_info.get('*'))
			target = doc_type_info.get('*')
			
			#target = contexto_info.get('reader').get(tipo, contexto_info) #get('*').get('*')
			routing_key = '%s.%s' % (contexto, target)
			if self.workflow['global']['fields'][tipo] and not upsert:
				#Caso não seja inserir, apenas atualizar, pode limitar os campos que são trafegados.
				#Adiciona o campo control, caso ele esteja presente. Esse campo é preenchido por demais filtros
				if 'control' not in self.workflow['global']['fields'][tipo]:
					self.workflow['global']['fields'][tipo].append('control')
				if not tipo == 'forum':
					to_publish = dict_find(paths=self.workflow['global']['fields'][tipo], dic=doc)
				else:
					to_publish = doc
			else:
				to_publish = doc
		
			self.publish(EXCHANGE_NAME, routing_key, self.encode(to_publish), durable=True)
			
			return (EXCHANGE_NAME, routing_key)
		except AttributeError:
			raise
			logger.warn(u"Ignorando dados de contexto desconhecido (%s) ou por exceção (%s)", contexto, sys.exc_info()[1])
	
	def process(self):

		def back_pressure(*args, **keywords):
			logger.warn("Back pressure, dormingo por 5s.")
			time.sleep(5)
			logger.warn("Processo acordou depois de back pressure")

		self.set_backpressure_multiplier(1)
		self.add_backpressure_callback(back_pressure)

		mongodb = self.workflow['global']['mongodb']['host']
		conn = pymongo.Connection(mongodb, slave_okay=False)
		oplog = conn.local['oplog.rs']
		br_tz = pytz.timezone('America/Sao_Paulo')

		'''
		enabled_contexts = self.workflow['global']['contexts']		
		#@FIXME: tempo
		last = br_tz.localize(datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(seconds=1*3600)).astimezone(pytz.utc)
		collection_expr = re.compile(r'coleta_(%s)\.(tweets|facebook|youtube|forum|instagram)_(%s)' % ('|'.join(enabled_contexts), '|'.join(enabled_contexts)))
		'''
		last = br_tz.localize(datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(seconds=1*3600)).astimezone(pytz.utc)
		
		db_collection = "%s.%s" % (self.workflow['global']['mongodb']['database'], self.workflow['global']['mongodb']['collection'])
		filtro = {'ns': db_collection, 'op': 'i'}
		max_date = None
		counter = 0
		logger.info("Lendo dados do backlog: passado (%s)", last)
		for obj in oplog.find(filtro, timeout=False).sort('$natural', pymongo.DESCENDING):
			inserted_at = obj['ts'].as_datetime()
			if max_date is None:
				max_date = obj['ts']
			source = db_collection#.findall(obj['ns'])		
			if inserted_at < last:
				break
			#contexto, tipo = source[0][0:2]
			contexto = self.workflow['global']['contexts'][0]
			tipo = 'tweets'
			
			self.publish_doc(obj['o'], tipo, contexto, obj['ns'])
			counter += 1
			if counter % 1000 == 0:
				logger.debug("Processados %s documentos (%s)", counter, obj.get('ts').as_datetime())
		# Usa o oplog do MongoDb. Essa coleção é usada para a replicação (replica set habilitado). 
		# Toda operação de inserção, atualização ou remoção é registrada nesse log. 
		# Entretanto, a coleção não possui nenhum índice (desempenho) e nem deve ter. 
		# Para usá-la, ordena-se por $natural desc (ordem de inserção decrescente), até atingir o
		# último documento processado. 
		# Daí usa-se um cursor especial que parte da última posição até um momento no tempo 
		# especificado por ts e segue adiante. Note que o cursor deve ser capaz de "descobrir" inserções (tailable).
		# Marca o ponto atual. Pode haver alguma sobreposição.
		filtro['ts'] = {'$gte': max_date}
		logger.info("Iniciando com backlog: presente")
		while True:
			cursor = oplog.find(filtro, tailable=True, timeout=False)
			cursor.add_option(8) #OpLogReplay: a partir do ponto atual
			while cursor.alive:
				try:
					found = False
					for obj in cursor:
						source = db_collection#.findall(obj['ns'])		
						#contexto, tipo = source[0][0:2]
						contexto = self.workflow['global']['contexts'][0]
						tipo = 'tweets'
				
						self.publish_doc(obj['o'], tipo, contexto, obj['ns'])
						counter += 1
						if counter % 1000 == 0:
							logger.debug("Processados %s documentos (%s)", counter, obj.get('ts').as_datetime())
						found = True
					if not found:
						time.sleep(1)
				except KeyboardInterrupt:
					logger.warn("Terminando...")
					sys.exit(0)
					
	def read_db(self, collection_name, inicio, fim, ignore_processed, coleta_id = None):
		expr = re.compile(r'(coleta_\d+)\.(tweets|facebook|youtube|forum|instagram)_(\d+)')
		
		mongodb = self.workflow['global']['mongodb']
		if isinstance(mongodb, basestring):
			mongodb = [mongodb]
		conn = pymongo.MongoClient(','.join(mongodb), read_preference=pymongo.ReadPreference.SECONDARY_PREFERRED)
		
		inicio = pytz.utc.localize(inicio)
		fim = pytz.utc.localize(fim)
		
		source = expr.findall(collection_name)
		db_name, tipo, contexto = source[0][0:3]
		
		collection = conn[db_name]['%s_%s' % (tipo, contexto)]
		filtro = {DATE_FIELD[tipo]: {'$gte': inicio, '$lt': fim}}
		
		if coleta_id:
			filtro['control.coleta.id'] = int(coleta_id)
		print filtro, collection
		logger.info(u"Usando como entrada coleção %s. Servidor: %s", collection, self.workflow['global']['mongodb'])
		logger.debug("Filtro: %s", filtro)
		if ignore_processed:
			filtro['control.update'] = {"$exists": False}
		for i, doc in enumerate(collection.find(filtro, timeout=False)):
			self.publish_doc(doc, tipo, contexto, collection_name)
			if i and i % 1000 == 0:
				logger.info(u"Processados %s documentos (%s)", i, doc[DATE_FIELD[tipo]])
				
	def read_file(self, filename, collection_name, coleta_id):
		
		expr = re.compile(r'(coleta_\d+)\.(tweets|facebook|youtube|forum|instagram)_(\d+)')
		source = expr.findall(collection_name)
		db_name, tipo, contexto = source[0][0:3]  # @UnusedVariable
		
		with open(filename, 'r') as f:
			for i, line in enumerate(f):
				try:
					doc = simplejson.loads(line)
					doc['_id'] = doc['id']
					doc['control'] = {'coletas': [{'id': int(coleta_id)}]}
					doc['created_at'] = datetime.datetime(*eut.parsedate(doc['created_at'])[:6])
					self.publish_doc(doc, tipo, contexto, collection_name, upsert=True)
				except Exception, e:
					print e.message
					pass
				print source
				print contexto		
				if i and i % 1000 == 0:
					logger.debug(u"Processados %s documentos (%s)", i, doc[DATE_FIELD[tipo]])
				
	def read_queue(self):
		logger.info("Lendo dados a partir da fila")
		try:
			self.consume(EXCHANGE_NAME, '#.reader.#', self.callback, durable=True, ack=True, queue='reader')
		except KeyboardInterrupt:
			logger.warn("Terminando...")
			
	def callback(self, channel, method, properties, body):
		item = self.decode(body)
		partes = method.routing_key.split('.')
		contexto = partes[-2]
		
		tipo = partes[0]
		collection_name = 'coleta_{0}.{1}_{0}'.format(contexto, tipo)
		if 'limit' in item or 'disconnect' in item: #Limitado pelo Twitter, ignora
			return
		#upsert = True para forçar o filtro updater a gravar o documento caso ele não exista
		self.publish_doc(item, tipo, contexto, collection_name, upsert=True) 
		channel.basic_ack(delivery_tag = method.delivery_tag)
		self.counter += 1
		if self.counter % 1000 == 0:
			logger.debug("Processados %s documentos (%s)", self.counter, item[DATE_FIELD[tipo]])
	
def create_exchanges_queues_bindings(connection, filas=[]):
	logger.info(u"Criando exchanges, filas e associações")
	channel = connection.channel()

	channel.exchange_declare(exchange=EXCHANGE_NAME, durable=True, type='topic')
	
	for filter_name in FILTERS.keys():
		channel.queue_declare(queue=filter_name, durable=True)
		channel.queue_bind(exchange=EXCHANGE_NAME, queue=filter_name, routing_key='#.%s.#' % filter_name)
		
	#channel.close() <- Bug, nunca fecha
	connection.close()
	logger.info("Filas criadas")

def purge_queues(connection):
	logger.info(u"Limpando as filas")
	resp = raw_input("Todas as filas serão limpas e o seu conteúdo perdido. Você tem certeza (s/N)?\n> ")
	if resp in ('S', 's'):
		channel = connection.channel()
	
		for filter_name in FILTERS.keys():
			channel.queue_delete(queue=filter_name)

		logger.info("Filas limpas")
	
def generate_supervisor_config(workflow):
	sources = ['tweets', 'facebook', 'instagram', 'news', '*']
	num_instances = {'reader': 1, 'em_import': 1, 'trends': 1, 'map': 1}
	reachable = set(['reader'])
	
	base_dir = raw_input('Qual o diretório base para os filtros?\n(/scratch/processamento/src) > ')
	if not base_dir:
		base_dir = '/scratch/processamento/src'
		
	supervisor_dir = raw_input('Qual o diretório de configuração do supervisord ?\n(/scratch/supervisor) > ')
	if not supervisor_dir:
		supervisor_dir = '/scratch/supervisor'
	
	for ctx in workflow['global']['contexts']:
		for name in FILTERS.keys():
			v = workflow[ctx].get(name, {})
			for source in sources:
				if source in v:
					for v1 in v[source].values():
						reachable.update(v1.split('.'))
		with open('{}/include/{}.ini'.format(supervisor_dir, ctx), 'w') as out_file:
			for f in reachable:
				if f in FILTERS:
					result = '\n'.join(['[program:{FILTER}_{CTX}]',
						'command=/usr/bin/python {BASE_DIR}/pipeline/{FILTER}_filter.py -w {SUPERVISOR_DIR}/workflows/{CTX}.json -n {INSTANCES}',
						'process_name=%(program_name)s#%(process_num)s',
						'numprocs=1',
						'directory={BASE_DIR}',
						'autorestart=true',
						'startsecs=10',
						'user=ubuntu',
						'stdout_logfile=/tmp/{FILTER}_out_{CTX}.log',
						'stdout_logfile_backups=0',
						'stderr_logfile=/tmp/{FILTER}_err_{CTX}.log',
						'stderr_logfile_backups=0',
						'environment=PYTHONPATH={BASE_DIR}'])
					result = result.format(FILTER=FILTERS.get(f), CTX=ctx, INSTANCES=num_instances.get(f, 3), 
									BASE_DIR=base_dir, SUPERVISOR_DIR=supervisor_dir)
					print >> out_file, result, '\n'
	print u'Arquivos de configuração gerados em {}/include'.format(supervisor_dir)
	print u'Use os comandos reread e update no supervisorctl'
	
def run(workflow, project, server, vhost, user, passwd):
	ReaderFilter(workflow, project, BaseFilter.connect_to_mq(server, vhost, user, passwd)).process()
	'''
	conn = BaseFilter.connect_to_mq(server, vhost, user, passwd)
	f = ReaderFilter(workflow, project, conn=conn)
	f.process()
	if source == 'mongo':
		f.process()
	elif source == 'queue':
		f.read_queue()
	'''

if __name__ == '__main__':
	
	logger.info('Iniciando reader filter')

	main_routine_filter('reader', run)
	'''	
	parser = OptionParser()
	define_common_parameters(parser)
	parser.add_option("-a", "--arquivo", dest="arquivo", help=u"Lê dados de arquivo. O arquivo deve estar no formato JSON" , 
			metavar="ARQUIVO")
	parser.add_option("-o", "--only-create", dest="only_create", help=u"Apenas cria as filas, exchanges e bindings no RabbitMQ" , 
			action='store_true', metavar="ONLY")
	parser.add_option("-p", "--purge", dest="purge", help=u"Limpa o conteúdo das filas no RabbitMQ" , 
			action='store_true', metavar="PURGE")
	parser.add_option("-i", "--input", dest="input", help=u"Usa arquivo como entrada ao invés do MongoDB" , 
			metavar="INPUT")
	parser.add_option("-r", "--read_db", dest="read_db", help=u"Lê os dados do MongoDb, considerando uma faixa de datas" , 
			metavar="READ_DB", action='store_true', default=False)
	
	parser.add_option("-s", "--supervisor-conf", dest="supervisor", help=u"Gera o arquivo de configuração para o supervisord" , 
			metavar="SUPERVISOR", action='store_true', default=False)
	
	parser.add_option("-q", "--read_queue", dest="read_queue", help=u"Lê os dados diretamente da fila (chamada reader)." , 
			metavar="READ_QUEUE", action='store_true', default=False)
	parser.add_option("-d", "--data_inicial", dest="data_inicial", help=u"Data inicial (usado com -r), formato %Y%m%d%H e incluída (fechado)." , 
			metavar="DATAINICIAL")
	parser.add_option("-f", "--data_final", dest="data_final", help=u"Data final (usado com -r), formato %Y%m%d%H e não incluída (aberto)." , 
			metavar="DATAFINAL")
	parser.add_option("-c", "--collection", dest="collection", help=u"Nome do banco de dados e da coleção que está sendo lida." , 
			metavar="COLLECTION")
	
	parser.add_option("--coleta_id", dest="coleta_id", help=u"Id da coleta, se há mais de uma armazenada na coleção. Use junto com as opções -r e -c" , 
			metavar="COLETA_ID")
	parser.add_option("-k", "--ignore-processed", dest="ignore_processed", help=u"QUando usado com a opção -r, ignora itens já processados (que tenham campo 'control').", 
			action='store_true', metavar="IGNORE_PROCESSED")

	parser.add_option("-j", "--project", dest="project_name", help=u"Project" , metavar="PROJECT_NAME")
	parser.add_option("-t", "--host", dest="host", help=u"Host" , metavar="HOST")
	parser.add_option("-b", "--db", dest="db", help=u"Database" , metavar="DB")
	parser.add_option("-z", "--port", dest="port", help=u"Port to connect" , metavar="PORT")
	(options, args) = parser.parse_args()
	
	filas = FILTERS.keys()
	if options.project_name and options.host and options.db:
		if not options.port:
			port = 27017
		else:
			port = options.port
		mongoCon = MongoClient(host=options.host, port=port)
		db = getattr(mongoCon, options.db)
		
		project = db['project'].find_one({"name":options.project_name})
		
	else:
		parser.print_usage()
	
	if project:
		workflow = WorkflowLoader().load(dict(project['workflow']))
		server, vhost, user, passwd = [str(x) for x in workflow['global']['rabbitmq']]
		conn = BaseFilter.connect_to_mq(server, vhost, user, passwd)
		
		if options.only_create:
			create_exchanges_queues_bindings(conn, filas)
			sys.exit(0)
		elif options.purge:
			purge_queues(conn)
			sys.exit(0)
		#elif options.supervisor:
		#	generate_supervisor_config(workflow)
		#	sys.exit(0)
		else:
			filtro = ReaderFilter(workflow, conn=conn)
			
			if options.read_db:
				if  options.read_queue:
					print (u'Opções -i, -q e -r não podem ser usadas simultaneamente.').encode('utf8')
					parser.print_usage()
					sys.exit(1)
				if not (options.data_inicial and options.collection):
					parser.print_usage()
					sys.exit(1)
				else:
					inicio = datetime.datetime.strptime(options.data_inicial, '%Y%m%d%H')
					if not options.data_final:
						fim = inicio + datetime.timedelta(days=1)
					else:
						fim = datetime.datetime.strptime(options.data_final, '%Y%m%d%H')	
					filtro.read_db(options.collection, inicio, fim, options.ignore_processed, options.coleta_id)
			elif options.read_queue:
				args = [workflow, server, vhost, user, passwd, 'queue']
				start_filter(int(options.instances), workflow, options.pidfile, run, args=args)
			else:
				args = [workflow, server, vhost, user, passwd, 'mongo']
				start_filter(int(options.instances), workflow, options.pidfile, run, args=args)
	else:
		parser.print_usage()
	'''		

