import datetime
from pymongo import MongoClient
import os

MONGODB_SETTINGS = {
	'db': 'active_learning',
	'host' : 'mongodb4.ctweb.inweb.org.br'
}

reader_filter = '''[program:bigsea_reader_filter_{0}]
command=/usr/bin/python pipeline/reader_filter.py -j {0} -t {1} -b {2}
process_name=%(program_name)s#%(process_num)s
numprocs=1
directory=/scratch/bigsea_active_learning/processamento/src/
autorestart=true
startsecs=10
user=ubuntu
redirect_stderr=true
stdout_logfile=/var/tmp/filters/bigsea/%(program_name)s_out_%(process_num)s
stdout_logfile_maxbytes=1MB
stdout_logfile_backups=10
stdout_capture_maxbytes=1MB
stderr_logfile=/var/tmp/filters/bigsea/%(program_name)s_err_%(process_num)s
stderr_logfile_maxbytes=1MB
stderr_logfile_backups=10
stderr_capture_maxbytes=1MB
environment=PYTHONPATH=/scratch/bigsea_active_learning/processamento/src'''

supervisor_dir = "/scratch/supervisor/include/"
main_file_name = "{0}_reader_filter_active_learning.ini"

lac_config_training_file = "/scratch/bigsea_active_learning/processamento/lacServer/lac_active_learning_training_config.in"

def config_lac_training_file(insert, training_name, training_file):
	arq = open(lac_config_training_file, "r")
	lines = arq.readlines()

	training = {}
	quantity = -1	
	for line in lines:
		if quantity != -1:			
			train_location = line.split("\t")
			if not train_location[0] in training:
				training[train_location[0]] = train_location[1].replace('\n','')
		quantity += 1
	
	arq.close()
	os.remove(lac_config_training_file)
	arq = open(lac_config_training_file, "a")
	config = ""
		
	if insert:
		quantity = 1
		config += training_name + "\t" + training_file + "\n"
		new_file = open(training_file, "a")
		new_file.write("")
		new_file.close()
		for train in training:
			if not train == training_name:
				config += train + "\t" + training[train] + "\n"
				quantity += 1
	else:
		config += str(quantity-1) + "\n"
		training.pop(training_name, 0)
		for train in training:
			config = config + train + "\t" + training[train] + "\n"

	arq.write(str(quantity) + "\n" + config)
	arq.close()

def create_supervisord_file():
	global reader_filter, main_file_name, supervisor_dir
	
	mongoCon = MongoClient(host=MONGODB_SETTINGS['host'], port=27017)
	db = getattr(mongoCon, MONGODB_SETTINGS['db'])
	
	projects = db['project']
	projs = projects.find()	
	change = False
	
	for project in projs:
		name = project['name']
		mongodb = project['workflow']['global']['mongodb-updater']['mongodb']
		database = project['workflow']['global']['mongodb-updater']['db']
		training_name = project['workflow']['trains'][0]['name']
		training_file = project['workflow']['global']['classification-server']['training-file']
		
		tmp_reader_filter = reader_filter.format(name, mongodb, database)
		tmp_main_file_name = main_file_name.format(name)
		
		file_name = supervisor_dir + tmp_main_file_name
		if project['is_active']:
			if not os.path.isfile(file_name):
				supervisor_file = open(file_name, "a")
				supervisor_file.write(tmp_reader_filter)
				supervisor_file.close()
				#print "[{0}] - Created a new configuration file for supervisor: {1}".format(datetime.datetime.now(), file_name)
				config_lac_training_file(insert=True, training_name=training_name, training_file=training_file)
				change = True			
		elif not project['is_active']:
			if os.path.isfile(file_name):
				os.remove(file_name)
				#config_lac_training_file(insert=False, training_name=training_name, training_file=training_file)
				#print "[{0}] - Supervisor configuration file deleted: {1}".format(datetime.datetime.now(), file_name)
				change = True
	if change:
		print 1
	else:
		print 0

	mongoCon.close()

if __name__ == '__main__':
	create_supervisord_file()
