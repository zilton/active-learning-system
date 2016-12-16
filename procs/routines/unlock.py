# -*- coding: utf-8 -*-
import datetime
from pymongo import MongoClient
import time


MONGODB_SETTINGS = {
    'db': 'active_learning',
    'host' : 'mongodb4.ctweb.inweb.org.br'
}

def unlock_tweet():
    mongoCon = MongoClient(host=MONGODB_SETTINGS['host'], port=27017)
    unlock = getattr(mongoCon, MONGODB_SETTINGS['db'])
    
    coll = unlock['tweets']
    locks = coll.find({'control.lock' : {'$exists' : True}})
    found = False
    for lock in locks:
        now = datetime.datetime.utcnow()
        lock_time = lock['control']['lock']
        
        time = (now - lock_time).seconds
        
        if time > 3600:
            print lock['_id'], lock['control']['lock'] 
            lock['control'].pop('lock', None)
            coll.save(lock)
            found = True
    
    if not found:
        print "There were no blocked tweets."
    
    mongoCon.close()

if __name__ == '__main__':
    while True:
        unlock_tweet()
        time.sleep(600)
