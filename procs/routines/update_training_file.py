# -*- coding: utf-8 -*-
import datetime
from pymongo import MongoClient
import time


MONGODB_SETTINGS = {
	'db': 'active_learning',
	'host' : 'mongodb4.ctweb.inweb.org.br'
}

def get_active_learning_instances():
	mongoCon = MongoClient(host=MONGODB_SETTINGS['host'], port=27017)
	db = getattr(mongoCon, MONGODB_SETTINGS['db'])
	
	training_info = {}
	
	coll_labeled_tweets = db['labeled_tweets']
	projects = db['project']
	
	tweets = coll_labeled_tweets.find({'control.lac_line' : {'$exists' : True}})
	
	coll_training_tweets = db['training_tweets']
	count = 0
	
	for tweet in tweets:
		if not tweet['control']['project'] in training_info:
			project = projects.find({"name" : tweet['control']['project']})[0]
			project_training_file = project['workflow']['global']['classification-server']['training-file']
			training_info[tweet['control']['project']] = {"training-file": project_training_file, "tweets":[tweet]}
		else:
			training_info[tweet['control']['project']]["tweets"].append(tweet)
	
	for project in training_info:
		arq = open(training_info[project]["training-file"], "a")
		for tweet in training_info[project]["tweets"]:
			lac_line = tweet['control']['lac_line']
			arq.write(lac_line+"\n")
			tweet['control']['added_to_training_at'] = datetime.datetime.utcnow()
			coll_training_tweets.save(tweet)
			coll_labeled_tweets.remove({'_id':int(tweet['_id'])})        
			count += 1
		arq.close()
	
	mongoCon.close()
	#return "Was added " + str(count) + " tweets - " + str(datetime.datetime.utcnow())
	return count

if __name__ == '__main__':
	print get_active_learning_instances()
