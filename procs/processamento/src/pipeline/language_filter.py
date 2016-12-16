# -*- coding: utf-8 -*-
from pipeline.base_filter import BaseFilter, main_routine_filter
import languageIdentifier
import os
import re
import string

#from guess_language import guess_language

EXCHANGE_NAME = 'workflow-1.0'
VERSION=5
class LanguageFilter(BaseFilter):
	def __init__(self, workflow, project, conn=None):

		self.workflow = workflow
		self.project = project

		super(LanguageFilter, self).__init__('lang', conn, workflow)
		
		#Expressões que tentam retirar caracteres repetidos
		self.expr = [
			(re.compile('[%s\\\\]' % string.punctuation), ' '),
			(re.compile('^([rs])\\1'), '\\1\\1'),
			(re.compile('([rs])\\1$'), '\\1'),
			(re.compile('([^rs])\\1{1,}'), '\\1'),
			(re.compile('([\\S\\s])\\1{2,}'), '\\1')
		];
		self.counter = 0
		trigram_path = self.workflow['global']['trigrams']
		if trigram_path[0] != '/':
			#Usa caminho relativo a este arquivo
			trigram_path = os.path.abspath(os.path.join(os.path.dirname(__file__), trigram_path))
		if trigram_path[-1] != '/':
			trigram_path += '/'
		languageIdentifier.load(trigram_path) #@UndefinedVariable

	def process(self):
		try:
			self.consume(EXCHANGE_NAME, '#.lang.#', self.callback, durable=True, ack=True, queue='lang')
		except KeyboardInterrupt:
			print u'\nEncerrando...'

	def callback(self, channel, method, properties, body):		
		item = self.decode(body)
		text = self._remove_repetition(item['_tmp_']['text_full']).lower()
		
		
		lang_twitter = ""
		if item.has_key('lang'):
			lang_twitter = item['lang']
		elif 'retweeted_status' in item and 'lang' in item['retweeted_status']:
			lang_twitter = item['retweeted_status']['lang']	
		#Remove URLs, hashtags e mentions do texto
		
		if not item['_tmp_']['type'] == 'forum' and not item['_tmp_']['type'] == 'news':
			if item.has_key('entities'):
				partes = item['entities']['user_mentions'][:]
				partes.extend(item['entities']['urls'])
				partes.extend(item['entities'].get('media', []))
		
				partes = sorted(partes, cmp=lambda x, y: cmp(x['indices'][0], y['indices'][0]))
	
				offset = 0
				for entity in partes:
					entity['indices'] = [int(entity['indices'][0]), int(entity['indices'][1])]
					text = text[0:entity['indices'][0]-offset]  + text[entity['indices'][1]-offset:]
					
					offset += entity['indices'][1] - entity['indices'][0]

		for expr in self.expr:
			text = expr[0].sub(expr[1], text)
			
		lang_text_identified = languageIdentifier.identify(text.encode('utf8'), 300, 300) #@UndefinedVariable
		lang = lang_text_identified
		
		'''
			Bloco abaixo utilizado para identificação de idioma em fórum.
			Se 60% do texto for do idioma EN, é atribuido este idioma ao texto.
			Caso contrário, é atribuido o idioma PT ao texto.
		'''
		if (not lang == 'pt') and (item['_tmp_']['type'] == 'forum'):
			ER = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)
			ER1 = re.compile('(#.*?(\s|$))', re.IGNORECASE)
			tmp_text = ER1.sub('', ER.sub('', item['text']))
			
			identify_text = tmp_text.split('\n')
			dic_lang = {}
			
			for identify_part in identify_text:
				new_lang = languageIdentifier.identify(identify_part.encode('utf8'), 300, 300)
				if not dic_lang.has_key(new_lang):
					dic_lang[new_lang] = 1
				else:
					dic_lang[new_lang] = dic_lang[new_lang] + 1
			
			count_other_lang = 0
			count_en = 0
			for key in dic_lang:
				if key == 'en':
					count_en += dic_lang[key]
				else:
					count_other_lang += dic_lang[key]
			
			percentage_en = 0.0
			if count_en > 0:
				percentage_en = count_en / (count_other_lang + count_en)				
			
			if percentage_en > 0.6:
				lang = 'en'
			else:
				lang = 'pt'

		contexto = self.get_contexto(method, item)
		#Testa se a interface do Twitter está em português. 
		contexto_info = self.workflow.get(contexto).get('lang')
		# Avalia se o idioma configurado para a interface do usuário é pt. 
		if item['_tmp_']['type'] == 'tweets':
			langs = contexto_info.get('use-lang-if-equals', [])
			if lang_twitter in langs or True:
				if lang_text_identified != lang_twitter: #Conflito de idioma
					description = ""
					if item.has_key('user') and  item['user'].get('description', None):
						description = self._remove_repetition(item['user']['description']).lower()

					lang_score = {lang_text_identified: 1}
					if lang_twitter and lang_twitter.strip():
						lang_score[lang_twitter] = 1
					for l in langs:
						if l not in lang_score:
							lang_score[l] = 0
					#Tenta pela descrição do usuário
					if description.strip():
						lang_description_identified = languageIdentifier.identify(description.encode('utf8'), 300, 300)  # @UndefinedVariable
						#print "Descrip", description, lang_description_identified
						if lang_description_identified in lang_score:
							lang_score[lang_description_identified] += 1
					#Tenta pelo perfil do usuário
					if 'lang' in item['user']:
						profile_lang = item['user'].get('lang')
						if profile_lang in lang_score:
							lang_score[profile_lang] += 1
					sorted_score = sorted(lang_score.iteritems(), key=lambda x: x[1], reverse=True)
					if sorted_score[0][1] == 1:
						if item['user']['location']: #Apenas 1 voto
							location_lang = languageIdentifier.identify(item['user']['location'].encode('utf8'), 300, 300)
							if location_lang in lang_score:
								lang = location_lang
							elif 'pt' in lang_score and lang_score['pt']:
								lang = 'pt'
							else:
								lang = sorted_score[0][0]
						else:
							lang = lang_twitter
					elif sorted_score[0][1] == lang_score.get(lang_twitter, 0):
						lang = lang_twitter
					else:	
						lang = sorted_score[0][0]
					#print lang_score
					#if 'it' == lang:
					#	print lang_text_identified,"|", lang_twitter, "|", langs, "|", text, 
					#	print "Score", lang_score
					#	raw_input("Diferente ({}): {} {} , resultado: {} \n> ".format(item['_id'], lang_text_identified, lang_twitter, lang))
			#print '-' * 50
		#print lang, lang_twitter, lang_text_identified
		#marcacao da versao e operaciao

		if not item['_tmp_']['type'] == 'news':
			item['control']['last'] = 'LANG'
			item['control']['lang'] = {'lang': lang}
			self._fill_version_info(VERSION, item['control']['lang'])

		if not lang in ['pt','en','es']:
			lang = 'Unknown'
		try:
			doc_type_info = contexto_info.get(item['_tmp_']['type'], contexto_info.get('*')) 
			routing_key = '%s.%s' % (contexto, doc_type_info.get(lang, doc_type_info.get('*')))
			if item['_tmp_']['type'] == 'news':
	                        item['_tmp_'].pop('text_full')
        	                item['_tmp_']['type'] = lang + '_news'
                	        item.pop('agg_type')
                        	item.pop('type')
				item.pop('doc_id')
				print routing_key
				print item
			#print contexto_info, item['_id'], lang_twitter, routing_key
			#print item.get('lang'), item['control']['lang'], item['text']
			#print '-'*10
			#print lang
			#print '-'*10
			#raw_input('Pressione enter \n > ')
			self.publish(EXCHANGE_NAME, routing_key, self.encode(item), durable=True)
			#print routing_key, doc_type_info, lang, item['lang']
			channel.basic_ack(delivery_tag = method.delivery_tag)
		except AttributeError:
			print "Ignorando", contexto, item['_tmp_']['type'], lang 
			routing_key = "Nenhuma"
			if contexto == '201':
				print contexto_info.get(item['_tmp_']['type'], contexto_info.get('*')), contexto_info, '>>>', doc_type_info

		self.counter += 1
		if self.counter == 1000:
			print '[LANG] %d docs' % self.counter
			self.counter = 0
		
		return (EXCHANGE_NAME, routing_key)	
		#channel.basic_ack(delivery_tag = method.delivery_tag)
		
def run(workflow, project, server, vhost, user, passwd):
	LanguageFilter(workflow, project, BaseFilter.connect_to_mq(server, vhost, user, passwd)).process()
if __name__ == '__main__':
	main_routine_filter('lang', run)
