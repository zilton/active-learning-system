# -*- coding: utf-8 -*-
# Gera uma linha de entrada no LAC
import simplejson
try:
	from pipeline.util.filters import gen_NGrams, filter_accents, filter_charRepetition, filter_url, filter_numbers, \
		filter_stopwords, filter_stemmer
except:
	pass
	
import os
import re
import socket
import time

VALID_CHAR_EXPR=re.compile(r'[^A-Za-z0-9]+', re.UNICODE)
EXTRACT_LAC=re.compile( r'id= ([\d_]+) label= \d+ correct= \d+ prediction= (\d+).*? rules= (\d+) projection= ([^\s]+) .*? Score\[0\]= (\d\.\d+).*? Score\[1\]= (\d.\d+) .*? Score\[2\]= (\d.\d+).*') 
EXTRACT_LAC2=re.compile( r'Score\[\d+\]= (\d\.\d+)+')
EXTRACT_LAC3=re.compile( r'id= ([\d_]+) label= \d+ correct= \d+ prediction= (\d+).*? ranking= (\d+\.\d+).*? rules= (\d+) projection= ([^\s]+) .*? Score\[0\]= (\d\.\d+).*? Score\[1\]= (\d.\d+) .*? Score\[2\]= (\d.\d+).*')

def get_line(klass, doc_id, original_content, screen_name, stops=[], ngram_size=2):
	'''
	Formata a linha para envio para o classificador 
	'''
	if type(original_content) is str:
		original_content = unicode(original_content)
	if type(screen_name) is str:
		screen_name = unicode(screen_name)
		
	content = gen_NGrams(ngram_size,
		VALID_CHAR_EXPR.sub(' ',  
			filter_accents(
					filter_charRepetition(
						filter_url(original_content.lower())))), True, True, ngram_sep="_")
	
	content.add(filter_accents(screen_name))
	content = set(filter(lambda x: x not in stops, content))
	return genLAClinha(doc_id, klass, filter_numbers(filter_stopwords(content, stop_words=stops)))

def get_line_with_stemmer(klass, doc_id, original_content, screen_name, stops=[], lang="pt", ngram_size=2, 
						remove_stops_first=True):
	'''
	Formata a linha para envio para o classificador 
	'''
	if type(original_content) is str:
		original_content = unicode(original_content)
	if type(screen_name) is str:
		screen_name = unicode(screen_name)
		
	url = filter_url(original_content.lower())
	
	charRepetition = filter_charRepetition(url)
	
	accents = filter_accents(charRepetition).split(' ')
	if remove_stops_first:
		removed_stopwords = filter_stopwords(accents, stop_words=stops)
		final_content = VALID_CHAR_EXPR.sub(' ', ' '.join(filter_stemmer(removed_stopwords, lang=lang)))
	else:
		final_content = VALID_CHAR_EXPR.sub(' ', ' '.join(filter_stemmer(accents, lang=lang)))
	
	content = gen_NGrams(ngram_size, VALID_CHAR_EXPR.sub(' ', final_content), True, True, ngram_sep="_")
	content.add(filter_accents(screen_name))
	content = set(filter(lambda x: x not in stops, content))
	return genLAClinha(doc_id, klass, filter_numbers(content))

def genLAClinha (line_id, classe, content):
	result = [str(line_id), "CLASS=%d" % classe]
	for word in content:
		if word.strip():
			result.append("w=" + word)
	return ' '.join(result)

class LacException(Exception):
	pass
SOCKET_NAME='LAC'
class LacSocketCommunicator():
	def __init__(self, address, port, use_unix_socket=False):
		self.address = address
		self.port = port
		self.use_unix_socket = use_unix_socket
		self.socket_cache = {}
		
	def connect(self, name, clean=False):
		''' Retorna o socket para comunicação com o servidor LAC '''
		if clean or not self.socket_cache.has_key(name):
			if self.use_unix_socket:
				lac_socket= socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				if not os.path.exists('/var/run/lac/%s.socket' % name):
					raise LacException(u'UNIX socket does not exist: %s' % self.address)

				lac_socket.connect(self.address)
				self.socket_cache[name] = lac_socket
			else:
				lac_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				lac_socket.connect((self.address, self.port))
				self.socket_cache[name] = lac_socket
		
	def send_and_receive(self, name, msg, append_new_line=True, retries=10):
		''' Envio de dados para o servidor LAC, respeitando o formado de entrada. ''' 
		if append_new_line:
			final_msg = '{0}# {1}\n'.format(name, msg.encode('utf-8'))
		else:
			final_msg = '{0}# {1}'.format(name, msg.encode('utf-8'))
		
		result_line = ''
		while True:
			try:
				if not self.socket_cache.has_key(SOCKET_NAME):
					self.connect(SOCKET_NAME, clean=True)
				self.socket_cache[SOCKET_NAME].send(final_msg)
				result_line = self.socket_cache[SOCKET_NAME].recv(10000)
				break
			except socket.error: #Pode ter sido reiniciado
				self.connect(SOCKET_NAME, clean=True)
				time.sleep(1)
				print u"Aguardando socket para nome %s" % name
				retries -= 1
				if retries == 0:
					raise LacException(u"Alcançado o número máximo de tentativas de conexão com o LAC Server")
					break
		result_line = result_line.strip()
		try:
			return simplejson.loads(result_line)
		except:
			return result_line
	def __unicode__(self):
		return u'{}:{}'.format(self.address, self.port)	
if __name__=="__main__":
	lac = LacSocketCommunicator("localhost", 4444)
	resultado = lac.send_and_receive("dengue", "154899508206125000 CLASS=2 w=crise_do w= w=enchentes_e w=a_crise w=do_judiciario w=enchentes w=dengue_ w=crise w=acabaram w=da_dengue w=dengue w=judiciario_agora w=judiciario w=das_enchentes w=acabaram_com", retries=10)
	print resultado
