# -*- coding: utf-8 -*-

'''
Created on Nov 11, 2016

@author: Zilton Cordeiro Junior <zilton@dcc.ufmg.br>

'''
import math
from optparse import OptionParser
from collections import Counter
from pipeline.base_filter import BaseFilter, configure_filter_logging, define_common_parameters, start_filter
from pipeline.base_filter import main_routine_filter
from pipeline.util.load_workflow import WorkflowLoader
from operator import itemgetter

VERSION=1
EXCHANGE_NAME = 'workflow-1.0'

class SelectInstance(BaseFilter):
	def __init__(self, workflow, project, conn = None):

		self.workflow = workflow
		self.project = project
		super(SelectInstance, self).__init__('select_instance', conn, workflow=workflow)
		self.counter = 0
		self.instances = {}
		self.window = 150

	def process(self):
		try:
			self.consume(EXCHANGE_NAME, '#.select_instance.#', self.callback, durable=True, ack=True, queue='select_instance')
		except KeyboardInterrupt:
			print u'\nEncerrando...'
	
	def counter_cosine_similarity(self, instance=None, example=None):
		'''
			Count the similarity cosine between two Counter type.
			@instance: List of words
			@example: List of words
		'''
		instance = Counter(instance)
		example = Counter(example)
		
		terms = set(instance).union(example)
		dotprod = sum(instance.get(k, 0) * example.get(k, 0) for k in terms)
		magA = math.sqrt(sum(instance.get(k, 0)**2 for k in terms))
		magB = math.sqrt(sum(example.get(k, 0)**2 for k in terms))
		return dotprod / (magA * magB)
	
	def most_similar_instance(self):
		'''
		'''
		
		k = 20
		for instance in self.instances:
			sum_cosine = 0.0
			for example in self.instances:
				if not instance == example:
					sum_cosine += self.counter_cosine_similarity(instance['text'], example['text'])
			
			for classifier in instance['control']['classification']:
				classifier['representativity'] = (sum_cosine/k) * classifier['score']
				instance['representativity'] = classifier['representativity']
		
		self.instances = sorted(self.instances, key=itemgetter('representativity'), reverse=True)[:20]

	def select_instance(self, instances = []):
		index = -1
		min_rules = 1000000000000000
		min_score = 100000
		i = 0
		
		for instance, train in instances:
			rules = int(train['rules'])
			score = float(train['score'])
			
			if rules < min_rules:
				min_rules = rules
				min_score = score
				index = i
			elif rules == min_rules:
				if score <= min_score:
					min_rules = rules
					min_score = score
					index = i
			i += 1
		
		instance, train = instances[index]
		return instance

	def callback(self, channel, method, properties, body):
		doc = self.decode(body)
		contexto = self.get_contexto(method, doc)
		
		try:
			contexto_info = self.workflow.get(contexto).get('select_instance')
			doc_type_info = contexto_info = contexto_info.get("*", contexto_info.get('*'))
			target = doc_type_info.get("*", contexto_info.get('*'))
			routing_key = '%s.%s' % (contexto, target)
		except AttributeError:
			print "Ignorando"
		
		for train in doc['control']['classification']:
			if not self.project['name'] in self.instances:
				self.instances = {self.project['name'] : {train['training'] : []}}
			elif not train['training'] in self.instances[self.project['name']]:
				self.instances[self.project['name']] = {train['training'] : []}
			
			if len(self.instances[self.project['name']][train['training']]) == self.window:
				most_representative_doc = self.select_instance(self.instances[self.project['name']][train['training']])
				self.publish(EXCHANGE_NAME, routing_key, self.encode(most_representative_doc), True)
				self.instances[self.project['name']][train['training']] = []
			else:
				self.instances[self.project['name']][train['training']].append((doc,train))
			
			'''
			self.most_similar_instance()
			self.instances[0].pop('representativity', None)
			self.instances[-1].pop('representativity', None)
			
			most_representative_doc = self.instances[0]
			less_representative_doc = self.instances[-1]

			self.publish(EXCHANGE_NAME, routing_key, self.encode(most_representative_doc), True)
			self.publish(EXCHANGE_NAME, routing_key, self.encode(less_representative_doc), True)
			self.instances = []
			'''
			
		channel.basic_ack(delivery_tag = method.delivery_tag)
		
		self.counter += 1
		if self.counter % 100 == 0:
			print '[active_learning] %d docs' % self.counter
	
		return (EXCHANGE_NAME, routing_key)

def run(workflow, project, server, vhost, user, passwd):
	SelectInstance(workflow, project, BaseFilter.connect_to_mq(server, vhost, user, passwd)).process()

if __name__ == '__main__':  
	main_routine_filter('select_instance', run)
	

