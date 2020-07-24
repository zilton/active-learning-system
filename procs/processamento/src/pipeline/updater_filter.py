# -*- coding: utf-8 -*-
from pipeline.base_filter import BaseFilter, main_routine_filter
from pipeline.util import unUTM
import hashlib
import pymongo
import re
# import datetime
import os

#Versao 2: Remoção de UTM_TAGS e ignora URLS muito longas 
VERSION=2
EXCHANGE_NAME = 'workflow-1.0'
match_urls = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.‌​][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(‌​([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?«»“”‘’]))""", re.DOTALL)

class UpdaterFilter(BaseFilter):
	''' Atualiza docs processados no servidor de dados '''
	def __init__(self, workflow, project, conn=None):

		self.workflow = workflow
		self.project = project
		super(UpdaterFilter, self).__init__("update", conn, workflow)
		
		self.timestamp = None
		self.counter = 0
		self.pid = os.getpid()
		self.conn = pymongo.Connection(self.workflow['global']['mongodb-updater']['mongodb'], subordinate_okay=False)
		
	def process(self):
		try:
			self.consume(EXCHANGE_NAME, '#.update.#', self.callback, durable=True, ack=True, queue='update')
		except KeyboardInterrupt:
			print u'\nEncerrando...'

	def callback(self, channel, method, properties, body):

		item = self.decode(body, parse_dates=True)
		contexto = self.get_contexto(method, item)
		
		db_name = self.workflow['global']['mongodb-updater']['db']
		col_name = self.workflow['global']['mongodb-updater']['collection']
		collection = self.conn[db_name][col_name]
		
		contexto_info = self.workflow.get(contexto).get('update')
		doc_type_info = contexto_info.get("*", contexto_info.get('*')) 
		
		upsert = True
		copia = item.copy()
		
		try:
			collection.insert(copia, upsert=True)
		except:
			if upsert:
				collection.update({'_id': copia['_id']}, copia, upsert=True)
			else:
				itemUpdate = {}
				for key in item['control']:
					itemUpdate['control.'+key] = copia['control'][key]
				collection.update({'_id': copia['_id']}, {'$set': itemUpdate})

		action = "*"
		try:
			route = doc_type_info.get(action, doc_type_info.get('*'))
			
			if route == '#END#':
				routing_key = '%s.%s' % (contexto, route)
			else: 
				routing_key = '%s.%s' % (contexto, route)
				self.publish(EXCHANGE_NAME, routing_key, self.encode(item), durable=True)
			channel.basic_ack(delivery_tag = method.delivery_tag)
		except AttributeError:
			print "Ignorando", contexto, tmp_info['type'], action 
					
		self.counter += 1
		if self.counter == 1000:
			print '[UPDATE] %d docs [%s]' % (self.counter, str(item['_id']))
			self.counter = 0

		return (EXCHANGE_NAME, routing_key)

def run(workflow, project, server, vhost, user, passwd):
	UpdaterFilter(workflow, project, BaseFilter.connect_to_mq(server, vhost, user, passwd)).process()
if __name__ == '__main__':
	main_routine_filter('updater', run)
