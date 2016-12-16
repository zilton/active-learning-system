# -*- coding: utf-8 -*-
from pipeline.lac import LacException
import simplejson
class MethodMock():
	def __init__(self, method, routing_key=""):
		self.method = method
		self.routing_key = routing_key
		
		self.queue = "dummy"
		self.delivery_tag = "DELIVERY"

class TransportMock():
	def __init__(self, method):
		self.method = MethodMock(method)
		
class ChannelMock():
	def __init__(self):
		self.reset()
		
	def reset(self):
		self.exchanges = {}
		self.bindings = {}
		self.ack = False
			
	def exchange_declare(self, exchange, type, durable): #@ReservedAssignment
		if not self.exchanges.has_key(exchange):
			self.exchanges[exchange] = {}
			self.bindings[exchange] = {}
	
	def basic_publish(self, exchange, routing_key, body, properties):
		if not exchange in self.exchanges:
			self.exchanges[exchange] = {}
			
		if self.exchanges[exchange].has_key(routing_key):
			self.exchanges[exchange][routing_key].append(body)
		else:
			self.exchanges[exchange][routing_key] = [body]
	def queue_declare(self, queue, durable, exclusive=None):
		return TransportMock('queue')
	
	def queue_bind(self, exchange, queue, routing_key):
		self.bindings[exchange][queue] = routing_key
	
	def basic_consume(self, callback, queue, no_ack):
		pass
	def start_consuming(self):
		pass
	def basic_ack(self, delivery_tag):
		self.ack = True
	def get_ack(self):
		return self.ack
		
class RabbitConnectionMock():
	def __init__(self):
		self._channel = None
	
	def channel(self):
		if not self._channel:
			self._channel = ChannelMock()
		return self._channel
	
	def ensure_message(self, exchange, routing_key, do_test):
		docs = self._channel.exchanges.get(exchange, {routing_key: []}).get(routing_key, [])
		for _doc in docs:
			doc = simplejson.loads(_doc)
			if do_test(doc):
				return True
		return False
	
	def ensure_binding_queue(self, exchange, queue, routing_key):
		return self._channel.bindings.get(exchange, {queue: None}).get(queue, None) == routing_key	

class MongoCollectionMock():
	def __init__(self, db, name):
		self.actions = {"C": [], "U": [], "D": []}
		self.filename = name
		self.db = db
	def update(self, *args, **kwargs):
		self.actions['U'].append((args, kwargs))
	def insert(self, *args, **kwargs):
		self.actions['C'].append((args, kwargs))
	def pop(self, action):
		return self.actions[action].pop(0)
	def find_one(self,  *args, **kwargs):
		return []
	def __unicode__(self):
		return u'%s.%s' % (self.db, self.filename)	
		
class MongoDbMock():
	def __init__(self, name):
		self.collections = {}
		self.filename = name
	def __getitem__(self, key):
		if not self.collections.has_key(key):
			self.collections[key] = MongoCollectionMock(self.filename, key)
		return self.collections[key]

class MongoConnectionMock():
	def __init__(self):
		self.dbs = {}
		
	def __getitem__(self, key):
		if not self.dbs.has_key(key):
			self.dbs[key] = MongoDbMock(key)
		return self.dbs[key]

class MongoGridFSMock():
	def __init__(self):
		self.files = []
	def get_last_version(self, **kwarg):
		chave = kwarg.keys()[0]
		valor = kwarg[chave]
		
		if chave == 'filename':
			for _file in reversed(self.files):
				if _file.filename == valor:
					return _file
				
		for _file in reversed(self.files):
			if _file.metadata[chave] == valor: 
				return _file	
		return None
	
	def put(self, filename, metadata):
		self.files.append(MongoGridFSFileMock(filename=filename, metadata=metadata))
		
	def exists(self, filename):
		for _file in self.files:
			if _file.filename == filename:
				return True
		return False
		
		
class MongoGridFSFileMock():
	def __init__(self, filename, metadata=None, **kwargs):
		self.filename = filename
		if metadata:
			self.metadata = metadata
			return
		for filename, value in kwargs:
			self.metadata[filename] = value		
	
		

class LacMock():
	def __init__(self, address, port, use_unix_socket=False):
		self.offline = False
		self.results = []
	
	def add_result(self, values):
		
		default_values = {'id': 9999, 'label': 0, 'correct': 0,
					'prediction': 1, 'ranking':  0.5, 'entropy': '-nan',
					'rules': 100, 'projection': 0.02, 'avg_size': 3.0, 
					'Rel[0]': 0.000000,  'Score[0]': 0.0, 
					'Prec[0]': '-nan', 'Rec[0]': 0.000000, 'F1[0]': '-nan',
					'Rel[1]': 0.000000,  'Score[1]': 0.0, 
					'Prec[1]': '-nan', 'Rec[1]': 0.000000, 'F1[1]': '-nan',
					'Rel[2]': 0.000000,  'Score[2]': 0.0, 
					'Prec[2]': '-nan', 'Rec[2]': 0.000000, 'F1[2]': '-nan',
					'Rel[3]': 0.000000,  'Score[3]': 0.0, 
					'Prec[3]': '-nan', 'Rec[3]': 0.000000, 'F1[3]': '-nan',
					'Rel[4]': 0.000000,  'Score[4]': 0.0, 
					'Prec[4]': '-nan', 'Rec[4]': 0.000000, 'F1[4]': '-nan'
		}
		default_values.update(values)
		lac_line = "id= %(id)d label= %(label)d correct= %(correct)d prediction= %(prediction)d " + \
					"ranking= %(ranking)f entropy= %(entropy)s rules= %(rules)d projection= %(projection)f avg_size= %(avg_size)f " + \
					"Rel[0]= %(Rel[0])f Score[0]= %(Score[0])f Prec[0]= %(Prec[0])s Rec[0]= %(Rec[0])f F1[0]= %(F1[0])s " + \
					"Rel[1]= %(Rel[1])f Score[1]= %(Score[1])f Prec[1]= %(Prec[1])s Rec[1]= %(Rec[1])f F1[1]= %(F1[1])s " + \
					"Rel[2]= %(Rel[2])f Score[2]= %(Score[2])f Prec[2]= %(Prec[2])s Rec[2]= %(Rec[2])f F1[2]= %(F1[2])s " + \
					"Rel[3]= %(Rel[3])f Score[3]= %(Score[3])f Prec[3]= %(Prec[3])s Rec[3]= %(Rec[3])f F1[3]= %(F1[3])s " + \
					"Rel[4]= %(Rel[4])f Score[4]= %(Score[4])f Prec[4]= %(Prec[4])s Rec[4]= %(Rec[4])f F1[4]= %(F1[4])s "
		#print lac_line % default_values
		self.results.append(lac_line % default_values)
		
	def pop(self):
		return self.results.pop(0)
	def size(self):
		return len(self.results)
	def connect(self, name, clean=False):
		pass
	def send_and_receive(self, name, msg, append_new_line=True, retries=10):
		if self.offline:
			raise LacException(u"Alcançado o número máximo de tentativas de conexão com o LAC Server")
		return self.pop()
	
	def go_offline(self):
		self.offline = True
		
class ElasticSearchIndexerMock():
	def __init__(self, url):
		self.url = url
			
	def index(self, doc_id, doc, path):
		pass
	def create_index_specifications(self, path, resource):
		pass
		


