# -*- coding: utf-8 -*-
import json
import unicodedata
import urlparse


try:
	import MySQLdb
except ImportError:
	import pymysql as MySQLdb
	MySQLdb.install_as_MySQLdb()

def strip_accents(s):
	return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))

class WorkflowDbStore:
	def __init__(self, dashboard_db_params, contexto = None, global_conf={}):
		if contexto is not None:
			self.contexto = int(contexto)
		else:
			self.contexto = None
		self.dashboard_db_params = dashboard_db_params
		self.global_conf = global_conf
		
	def _carregar_parametros_term_filter(self, c, cursor):
		'''
		Recupera os parâmetros para filtro de termos. 
		'''
		#Termos que são substituídos
		
		LISTA_SUBSTITUICAO = 4
		cursor.execute('''SELECT valor FROM comum_lista WHERE habilitada = 1 AND contexto_id = %s AND tipo = %s''', 
					[self.contexto, LISTA_SUBSTITUICAO])
		c['term']['regex-replace'] = []
		for row in cursor:
			c['term']['regex-replace'].extend([x.strip() for x in row[0].split(',')])
		
	def _carregar_parametros_processamento(self, c, cursor):
		cursor.execute('''SELECT p.slug, p.nome, pc.valor FROM comum_parametro p 
							JOIN comum_parametrocontexto pc ON pc.parametro_id = p.id 
							WHERE contexto_id = %s''', [int(self.contexto)])
		parametros = {}
		for row in cursor:
			slug, _, valor = row
			if valor.find('//') == -1 and valor:
				valor = '//' + valor
			parsed = urlparse.urlparse(valor)	
			parametros[slug] = valor
			#Coisas legadas
			if 'data-db' == slug:
				c["global"]["mongodb"] = parsed.netloc #@FIXME: COmo especificar múltiplos servidores
			elif 'geo-search-server' == slug and valor:
				db, table = parsed.path[1:].split('/', 2)
				c["global"]["geo-cache"] = [parsed.hostname, db, table, parsed.username, parsed.password, parsed.port]
			elif 'index-server' == slug:
				c["global"]["index"] = {"version": parsed.scheme, "server": "{}:{}".format(parsed.hostname, parsed.port or '80')
									, "username": parsed.username, "password": parsed.password}
			elif 'lac-server-disambiguation' == slug:
				c["global"]["lac-server"] = [parsed.hostname, parsed.port]
			elif 'lac-server-classification' == slug:
				c["global"]["lac-classification-server"] = [parsed.hostname, parsed.port]
			elif 'portal-db' == slug:
				c["global"]["db-observatorio"] = [parsed.hostname, None, parsed.path.replace('/',''), parsed.username, parsed.password, parsed.port if parsed.port else 3306]
			elif 'queue-server' == slug:
				if parsed.scheme == '' or parsed.scheme == 'rabbitmq':
					if 'rabbitmq' in self.global_conf:
						c["global"]["rabbitmq"] = self.global_conf['rabbitmq']
					else:
						c["global"]["rabbitmq"] = [str(x) for x in [parsed.hostname, parsed.path, parsed.username, parsed.password]]
				elif parsed.scheme == 'nsq':
					c["global"]["mq"] = [str(x) for x in ['{}://{}'.format(parsed.scheme, parsed.hostname), 
														parsed.path, parsed.username, parsed.password]]
			
			#Para processamento de perfil de usuário
			elif 'crawler-queue-server' == slug:
				c["global"]["caracterizacao"]["fila_coletor"] = {
								"servidor": parsed.hostname, "porta": parsed.port, "vhost": parsed.path, 
								"usuario": parsed.username, "password": parsed.password
				}
			elif 'profile-mongodb-server' == slug and parsed.path:
				db, table = parsed.path[1:].split('/', 2)
				c["global"]["caracterizacao"]["mongodb"] = {
					"servidor": parsed.hostname, "db": db, "colecao": table
				}
			elif 'weka-server' == slug:
				c["global"]["caracterizacao"]["classificador"] = {
								"servidor": parsed.hostname, "porta": parsed.port
				}
			
		c['params'] = parametros
		cursor.execute('SELECT nome, parametros_processamento FROM comum_contexto WHERE id = %s', [self.contexto])
		row = cursor.fetchone()
		
		if row:
			_, parametros_processamento = row
			if parametros_processamento:
				obj = json.loads(parametros_processamento)
				for node in obj['nodes']:
					node_id = node['id']
					if 'form' in node:
						form = dict(map(lambda x: (x['id'], x['v']), node['form']))
						if node_id in ('lac_classifier', 'rules', 'entity', 'unload', 'update'):
							pass
						elif node_id == 'reader':
							c['reader']['use-nsq'] = form.get('usar-nsq', False)
						elif node_id == 'lang':
							if 'usar-perfil' in form and form['usar-perfil']:
								c['lang']['use-lang-if-equals'] = [x.strip() for x in form['usar-perfil'].split(',') if x.strip()]
						elif node_id == 'term':
							if 'stemming' in form and form['stemming'] and form['stemming'] != '-':
								c['term']['stemmer'] = form['stemming']
							else:
								c['term']['stemmer'] = None
						elif node_id in ('url', 'geo'):
							if 'usar-proxy' in form:
								#c[node_id] #@FIXME: Implementar no filtro a opção de configuração. Adicionar servidor de proxy
								pass
							if 'extract-title-and-image' in form:
								c[node_id]['extract-title-and-image'] = form['extract-title-and-image']
						elif node_id == 'em_import':
							c['em_import']['size'] = int(form.get('tamanho') or 1000)
							c['em_import']['interval'] = int(form.get('intervalo') or 600)
						elif node_id == 'pending':
							c['pending']['sleep'] = int(form.get('intervalo', '60') or 60)
						elif node_id == 'map':
							c['map']['size'] = int(form.get('tamanho') or 1000)
							c['map']['interval'] = int(form.get('intervalo') or 600)
						else:
							print "FIXME: Implementar", form, node_id
				
				stage = set()
				types = set()
				for edge in sorted(obj['edges'], key = lambda x: x['source']):
					#print '@@@', c['rule'], edge['source']
					if edge['source'] in ('reader', 'lang') or True:
						if edge['source'] not in c:
							c[edge['source']] = {}
						
						stage.add(edge['source'])
						for f in [x for x in edge['form'] if x['v']]:
							doc_type, result = f['v'].split(',', 2)
							types.add(doc_type)
							'''if edge['source'] == 'rule':
								print '-' * 10
								print doc_type not in c[edge['source']]
								print c[edge['source']], doc_type
								print '-' * 10
							''' 
							if doc_type not in c[edge['source']]:
								c[edge['source']][doc_type] = {result: edge['target']}
							else:
								if result in c[edge['source']][doc_type]: # Mais de um filtro é alvo com o mesmo resultado
									c[edge['source']][doc_type][result] += '.' + edge['target']
								else:
									c[edge['source']][doc_type][result] = edge['target']
							#print edge, edge['source'], edge['target']
							
				#print f['v'],
				# Trata o caso onde para qualquer tipo de fonte, tem que haver encaminhamento, mas também
				# existe uma regra específica. Por exemplo tweets,* -> em_import e *,* -> entity. 
				# Neste caso, o resultado tem que ser tweets,*-> em_import.entity e *,* -> entity
				#print '>>', c['entity']
				# Aparentemente, não precisa! Walter - 13/03/2014
				'''
				for s in stage:
					if '*' in c[s]:
						value = c[s]['*'].get('*', '')
						for t in types:
							if t in c[s] and t != '*':
								if '*' in c[s][t]:
										c[s][t]['*'] = c[s][t]['*'] + '.' + value
								else:
									c[s][t]['*'] = value
				'''
			#fim if
	def _carregar_parametros_entity_filter(self, c, cursor):
		''' Filtro de regras: identifica hashtags, mentions e expressões "fortes" para identificar entidade '''
		
		# Carrega as associações do tipo IMPLICA = 1. Isto significa que se a origem for identicada, o destino
		# também é. Por exemplo, identificando Dilma => Brasil ou Dilma => PT
		cursor.execute('''SELECT origem_id, destino_id FROM entidade_associacaoentidade ea
							JOIN entidade_entidade e ON ea.origem_id = e.id
							WHERE contexto_id = %s AND tipo = %s ORDER BY 1''', [int(self.contexto), 1])
		associados = {}
		for origem_id, destino_id in cursor:
			if origem_id not in associados:
				associados[origem_id] = []
			associados[origem_id].append(destino_id)
		
		cursor.execute('''SELECT id, expressoes_fortes, expressoes_fracas, expressoes_combinadas 
						FROM entidade_entidade 
						WHERE contexto_id = %s AND habilitada = 1 ''', [int(self.contexto)])
		for (_id, fortes, fracas, combinadas) in cursor:
			expressoes_fortes = set([strip_accents(p.strip().lower()) for p in fortes.split(',') if p.strip()])
			expressoes_fracas = set([strip_accents(p.strip().lower()) for p in fracas.split(',') if p.strip()])
			expressoes_combinadas = set([strip_accents(p.strip().lower()) for p in combinadas.split(',') if p.strip()])
		
			identificadores = [_id] + associados.get(_id, [])
			for p in expressoes_fortes:
				if p[0] == '#':
					if not p in c['rule']['hashtags']:
						c['rule']['hashtags'][p] = set()
					c['rule']['hashtags'][p].update(identificadores)
				elif p[0] == '@':
					if not p in c['rule']['users']:
						c['rule']['users'][p] = set()
					c['rule']['users'][p].update(identificadores)
				else:
					if not p in c['rule']['sequences']:
						c['rule']['sequences'][p] = set()
					c['rule']['sequences'][p].update(identificadores)
		
			for p in expressoes_combinadas:
				c['rule']['itemsets'].append([identificadores, [[x.strip() for x in p.split(' ')] ]])
				
			c["entity"]["terms"].append(
					{ "_id" : _id, "terms" : list(expressoes_fracas) })
		
		#@FIXME: Como definir regras baseadas em "versus"? É combinação de todos com todos. Talvez usar campo "conector" e "expressão de conexão". Ex: vs, x, - e Atletico-MG
		#@FIXME: Avaliar se há como melhorar a parte de artigos.
		#@FIXME: Falta c["entity"]["reverse-translations"]
	def load(self):
		(mysql_server, db_vis, user, passwd, port) = self.dashboard_db_params
		conn = MySQLdb.connect(host = mysql_server, port=port, 
										user = user, passwd = passwd,
										db = db_vis, use_unicode=True, charset = 'utf8')
		
		cursor = conn.cursor()
		
		if self.contexto is not None:
			contextos = [str(self.contexto)]
		else:
			contextos = [str(row[0]) for row in cursor.execute('SELECT id FROM comum_contexto WHERE habilitado = 1')]
		
		result = {}
		for ctx in contextos:
			result = {ctx: { } }
			
			c = result[ctx]
			c["global"] = {}
			c["global"]["caracterizacao"] = {}
			c["reader"] = {}
			c["lang"] = {}
			c["term"] = {"use-entity-info" : True}
			c["geo"] = {}
			c["map"] = {}
			c["url"] = {}
			c["entity"] = {}
			c["em_import"] = {}
			c["update"] = {}
			c["caracterizacao_usuario"] = {}
			c["sentimento"] = {}
			c["pending"] = {'sleep': 60}
			
			c["rule"] = { "hashtags": {}, "sequences": {}, "users": {}, "itemsets":[] };
			
			
			self._carregar_parametros_term_filter(c, cursor)
			c["entity"].update({ "stemmer": c['term'].get('stemmer'), "terms": [] })
			self._carregar_parametros_entity_filter(c, cursor)
			#Deve ser a última ação a ser executada
			self._carregar_parametros_processamento(c, cursor)
			#print c['rule']['*'], c['rule']['tweets'], c['rule']['facebook']
		return result

	
if __name__ == '__main__':
	pass
