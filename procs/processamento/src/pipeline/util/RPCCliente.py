import pika
import simplejson
import uuid

class RPCClient():
	def __init__(self, server, port, vhost, user, password):
		self.server = server
		self.port = port
		self.vhost = vhost
		self.user = user
		self.password = password

		credentials = pika.PlainCredentials(user, password)
		connectionParameters = pika.ConnectionParameters(host=server,
														 port=port,
														 virtual_host=vhost,
														 credentials=credentials)
		self.connection = pika.BlockingConnection(connectionParameters)
		self.channel = self.connection.channel()
		result = self.channel.queue_declare(exclusive=True)
		self.callback_queue = result.method.queue
		
		self.channel.basic_consume(self.on_response,
								   no_ack=True,
								   queue=self.callback_queue)
		
	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body
	'''
	A mensagem enviada para o rabbit tem o seguinte formato
	item = {'usuario':usuario_id, 
			'tarefa':{'nome':<get_followings, get_followers, get_tweets>, 'max': int},
			'salva':[{salva:url}],
			'mongo_servidor': mongo_servidor, 
			'mongo_bd':bd_mongo, 
			'mongo_colecao':colecao_mongo 
			}
	'''
	def publica_coletor(self, tarefa, maximo, usuario, mongo_servidor, mongo_db, mongo_colecao):
		url = 'mongodb://%s/%s/%s' % (mongo_servidor, mongo_db, mongo_colecao)

		mensagem = simplejson.dumps({'usuario':usuario, 
									 'tarefa':{'nome':tarefa,'maximo':maximo},
									 'salva': [{'mongo':url}],
									 'mongo_servidor':mongo_servidor,
									 'mongo_db':mongo_db,
									 'mongo_colecao':mongo_colecao
									 })
		
		self.response = None
		
		self.corr_id = str(uuid.uuid4())
		self.channel.queue_declare( queue='coletor_%s'%tarefa, durable=True )
		self.channel.basic_publish(exchange="",
									routing_key='coletor_%s'%tarefa,
								   properties=pika.BasicProperties(
										reply_to=self.callback_queue,
										correlation_id=self.corr_id,
										delivery_mode = 2, #persistent
								  ),
								   body=mensagem)

		while self.response is None:
			self.connection.process_data_events()
		
		self.connection.close()
		return self.response