# -*- coding: utf-8 -*-
from pipeline.base_filter import BaseFilter, main_routine_filter
from pipeline.util import filters
import pipeline.lac as lac
import os
import sys
import datetime
from pymongo import MongoClient

#EXTRACT_LAC3 = re.compile(r'([\w\[\]\d]+)=\s([\d+\.]+)')
EXCHANGE_NAME = 'workflow-1.0'
VERSION = 1

class LacResult():
	def __init__(self, result, rules_count, projection, ranking, num_transactions, min_support, scores):
		self.result = result
		self.rules_count = rules_count
		self.projection = projection
		self.num_transactions = num_transactions
		self.min_support = min_support
		self.ranking = ranking
		
		assert type(scores) == list
		self.scores = scores
	def update_result_by_thresholds(self, thresholds):
		''' 
		' Atualiza o resultado para incluir classes de acordo com um limiar.
		' Desta forma, permite classificação multiclasse e também que não seja o (maior) score 
		' o único determinante do resultado.
		'''
		for i, score in enumerate(self.scores):
			if i >= len(thresholds):
				break 
			if score >= thresholds[i][0]:
				if str(i) not in self.result: #Assume que as classes do LAC são números iniciados de zero.
					self.result.append(str(i))
			elif thresholds[i][1] == 'remove' and str(i) in self.result:
				self.result.remove(str(i))
					
	def as_dict(self, mappings, total_of_classes=2, full=False):
		result = {"result": []}
		for r in self.result:
			result['result'].append(mappings.get("result", {}).get(r, r))
		for i, score in enumerate(self.scores[:total_of_classes]):
			key = str(i)
			if mappings.get("classes", {}).has_key(key):
				result[mappings.get("classes", {})[key]] = float(score)
			else:
				result[key] = float(score)
		result["rules"] = int(self.rules_count) 
		if full:
			result["projection"] = float(self.projection)
			result["ranking"] = float(self.projection) 
			result["transactions"] = self.num_transactions 
			result["min_support"] = self.min_support
		return result
	
class LacClassifierFilter(BaseFilter):
	def __init__(self, workflow, project, lac_conn=None, conn=None):
		self.lac_line = ""
		self.workflow = workflow
		self.project = project
		self.project['workflow']['trains'] = []
	
		self.host = self.project['workflow']['global']['mongodb-updater']['mongodb']
		self.port = self.project['workflow']['global']['mongodb-updater']['port']
		self.db = self.project['workflow']['global']['mongodb-updater']['db']
		
		mongoCon = MongoClient(host=self.host, port=self.port)
		db = getattr(mongoCon, self.db)
		all_projects = db['project'].find()
		mongoCon.close()
		
		for proj in all_projects:
			for train in proj['workflow']['trains']:
				#train['project-name'] = self.project['name']
				self.project['workflow']['trains'].append(train)

		super(LacClassifierFilter, self).__init__('classifier', conn, workflow=workflow)
		
		if lac_conn:
			self.lac = lac_conn
		else:
			#Como proceder com a carga? uma instância só pode não aguentar...
			lac_server = self.workflow['global']['classification-server']['address']
			lac_port = self.workflow['global']['classification-server']['port']
			self.lac = lac.LacSocketCommunicator(lac_server, int(lac_port), False)
			
		self.counter = 0
		#Carrega as listas de stop words para a memória
		self.stops = {}
		for k, v in self.workflow['global']['stop-words'].iteritems():
			if v[0] == '/':
				stop_word_filename = v
			else:
				stop_word_filename = os.path.join(os.path.dirname(
					os.path.realpath(__file__)), v)
			with open(stop_word_filename, "r") as stop_file:
				data = stop_file.read()
				self.stops[k] = filters.filter_accents(data.decode('utf8')).split('\n')
		self.trains = {}
		for ctx in self.workflow['global']['contexts']:
			train = {}
			self.trains[ctx] = train
			for t in self.workflow[ctx].get('classifier', {}).get('trains', []):
				train[t['name']] = t
				
	def _classify_item(self, item, contexto, train_name, params, max_words, stops, ngram_size, use_stemmer=True, lang='pt', 
					remove_stops_first=True):
		
		doc_id = item['_id']
		user = ""
		
		text = item['text']
		
		words = text.split()
		if len(words) > max_words:
			text = ' '.join(words[0:max_words])
		if use_stemmer:
			lac_line = lac.get_line_with_stemmer(0, doc_id, text, user, stops=stops, ngram_size=ngram_size, 
										lang=lang, remove_stops_first=remove_stops_first)

		else:
			lac_line = lac.get_line(0, doc_id, text, user, stops=stops, ngram_size=ngram_size)
		self.lac_line = lac_line
		lac_result = self.lac.send_and_receive(train_name, lac_line)

		if type(lac_result) == str and lac_result[:24] == 'ERRO: Treino inexistente':
			raise NotImplementedError('{0}: {1}'.format(lac_result, doc_id))
		
		if type(lac_result) == str:
			parts = lac.EXTRACT_LAC3.findall(lac_result)
			(result, ranking, rules_count, projection) = parts[0][1:5]
			scores = [float(s) for s in lac.EXTRACT_LAC2.findall(lac_result)]
			num_transactions = 1.0 / float(projection)
			min_support = max([int(num_transactions)/2000, 4])

		elif type(lac_result) == dict:
			(result, ranking, rules_count, projection) = (lac_result['prediction'],0.0,lac_result['numRules'],0.0)
			scores = [value for (key, value) in sorted(lac_result['probabilities'].items())]
			num_transactions = 0.0
			min_support = 4
		
		try:
			return LacResult([result], rules_count, projection, ranking, num_transactions, min_support, scores)
		except:
			#Ocorre caso o apresendizado ativo tenha acabado de ser inicializado e o treino para o LAC estiver vazio.
			#Não acarreta problema no sistema.
			return LacResult(['not-defined'], 0, 0.0, 0.0, 0.0, 0, [0, 0.0, 0.0,0])
		
	def callback(self, channel, method, properties, body):
		item = self.decode(body, parse_dates=True)

		contexto = self.get_contexto(method, item)
		contexto_info = self.workflow.get(contexto).get('classifier')
		doc_type_info = contexto_info
		
		#doc_type_info['trains'] = self.project['workflow']['trains']
		host = self.project['workflow']['global']['mongodb-updater']['mongodb']
		port = self.project['workflow']['global']['mongodb-updater']['port']
		db = self.project['workflow']['global']['mongodb-updater']['db']
		mongoCon = MongoClient(host=host, port=port)
		database = getattr(mongoCon, db)
		projects = database['project']
		item_project = projects.find({"name":item['control']['project']})[0]
		#print item_project
		doc_type_info['trains'] = item_project['workflow']['trains']
		
		status_ok = True
		force_routing = None
		
		tweet_classified = {"_id" : item["_id"],
							"control" : {"active_learning" : {},
										 "coleta" : item["control"]["coleta"],
										 "classification" : [],
										 "project": item['control']['project']
										},
							"text" : item["text"],
							"created_at" : item["created_at"]}
		
		for trains in doc_type_info['trains']:
			language = None
			stop_option = trains.get('stop-word', 'pt')
			language = stop_option
			
			total_of_classes = trains.get('total-of-classes', 3)
			
			try:		
				lac_result = self._classify_item(item,
												 contexto, 
												   trains['name'],
												 trains.get('params'), 
												  trains.get('max_words', 1000),
												 stops=self.stops.get(language, []),
												 ngram_size=trains.get('ngram-size', 1),
												 lang=language,
												 use_stemmer=trains.get("stemmer", True),
												 remove_stops_first=trains.get('remove-stops-first', True))
				'''
				' Algumas classificações devem considerar limiares mínimos para que o resultado
				' inclua determinada classe.
				'''
				if 'thresholds' in trains:
					lac_result.update_result_by_thresholds(train['thresholds'])
			except NotImplementedError, nie:
				status_ok = False
				print >> sys.stderr, nie.message
				continue

			if not 'classification' in item:
				item['classification'] = {}
				item['classification'][trains['name']] = lac_result.as_dict(
							trains.get('mappings', {}), total_of_classes, trains.get("full", False))

				for r in lac_result.result:
					if 'on-result' in trains and r in trains['on-result']:
						force_routing = trains['on-result'][r]
			if status_ok:
				item["control"]["last"] = "classifier"
				self.counter += 1
				if (self.counter % 1000) == 0:
					print "Processados %d tweets (%s)" % (self.counter, str(item['_id']))
					self.counter = 0
				try:
					if force_routing:
						routing_key = '{0}.{1}'.format(contexto, force_routing)
					else:
						routing_key = '{0}.{1}'.format(contexto, doc_type_info.get("*", doc_type_info.get('*')))
					major_score = -1.0
					
					for t in item["classification"]:
						for r in item["classification"][t]:
							sentiment = item["classification"][t]["result"][0].lower()
							rules = item["classification"][t]["rules"]
							try:
								if item["classification"][t][r] >= 0.0 and item["classification"][t][r] <= 1.0:
									if float(item["classification"][t][r]) > major_score:
										major_score = float(item["classification"][t][r])
							except:
								pass
					
					control_classification = {"score" : major_score,
											  "rules" : rules,
											  "classifier" : trains.get('classifier', 'LAC'),
											  "classified_at" : datetime.datetime.utcnow(),
											  "sentiment" : sentiment,
											  "training" : trains.get('name', None)
											 }
					tweet_classified['control']['classification'].append(control_classification)
					tweet_classified['control']['lac_line'] = self.lac_line
					
					self.publish(EXCHANGE_NAME, routing_key, self.encode(tweet_classified), durable=True)
					channel.basic_ack(delivery_tag = method.delivery_tag)
				
				except AttributeError:
					print "Ignorando", contexto, item['_tmp_']['type']
					routing_key = "Nenhuma"
			
				return (EXCHANGE_NAME, routing_key)
		
	def process(self):
		try:
			self.consume(EXCHANGE_NAME, '#.classifier.#', self.callback, durable=True, ack=True, queue='classifier')
		except KeyboardInterrupt:
			print u'\nEncerrando...'

def run(workflow, project, server, vhost, user, passwd):
	LacClassifierFilter(workflow, project, conn=BaseFilter.connect_to_mq(server, vhost, user, passwd)).process()
if __name__ == '__main__':
	main_routine_filter('classifier', run)
