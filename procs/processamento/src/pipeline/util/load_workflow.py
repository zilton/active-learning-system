# -*- coding: utf-8 -*-
import imp
import os
import pprint
import sys

from pipeline.util.workflow_db_store import WorkflowDbStore
import simplejson as json

class WorkflowLoader():
		def load(self, workflow):
				ignorados = set()
				
				if workflow['global'].has_key('db-pipeline'):
						''' Carrega workflow a partir do banco de dados '''
						for ctx in workflow['global']['contexts']:
								x= WorkflowDbStore(workflow['global']['db-pipeline'], ctx).load()

								workflow.update(x)
								workflow['global'].update(workflow[ctx]['global']) #@FIXME: Como fazer cada contexto ter sua própria configuração inclusive para o RabbitMq?

				elif workflow['global'].has_key('workflow-dir'):
						directory = workflow['global']['workflow-dir']
						ctxs = [int(x) for x in workflow['global']['contexts']]
						if directory[0] != '/': #Caminho relativo
								directory = workflow['global']['workflow-dir']#os.path.abspath(os.path.join(os.path.dirname(workflow_file), directory))
						for f in filter(lambda name: name[-4:] == 'json', os.listdir(directory)):
								if int(f[:-5]) in ctxs:
										try:
												path_name = os.path.join(directory, f)
												if os.path.isfile(path_name):
														with open(path_name, 'r') as wf_extra:
																workflow.update(json.loads(wf_extra.read()))
										except:
												raise(Exception("Erro lendo %s: %s" % (f, sys.exc_info()[1])))
								else:
										ignorados.add(f[:-5])
						#Carrega arquivos no formato Python	 
						for f in filter(lambda name: name[-3:] == '.py', os.listdir(directory)):
								if int(f[1:-3]) in ctxs:
										config = imp.load_source(f[:-3], os.path.join(directory, f))
										workflow.update(config.context)
								else:
										ignorados.add(f[1:-3])
				print 'Contextos com configuracao, mas ignorados:', ', '.join(ignorados)
				workflow['base_path'] = workflow['global']['workflow-dir']#os.path.abspath(os.path.dirname(workflow_file))
				return workflow
	
if __name__ == '__main__':
	workflow = WorkflowLoader().load('../pipeline.json')
	pprint.pprint(workflow)
#	print pprint(workflow['204'])				
				
