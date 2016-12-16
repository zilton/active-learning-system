import datetime
try:
	import simplejson as json
except ImportError:
	import json
import decimal
class JSONEncoder(json.JSONEncoder):
	"""																			 
	JSONEncoder subclass that knows how to encode date/time and decimal types.	  
	"""
	DATE_FORMAT = "%Y-%m-%d"
	TIME_FORMAT = "%H:%M:%S"
	FULL_FORMAT =  "%Y-%m-%dT%H:%M:%S"

	def default(self, o):
		if isinstance(o, datetime.datetime):
			return o.strftime(self.FULL_FORMAT)
		elif isinstance(o, datetime.date):
			return o.strftime(self.DATE_FORMAT)
		elif isinstance(o, datetime.time):
			return o.strftime(self.TIME_FORMAT)
		elif isinstance(o, decimal.Decimal):
			return str(o)
		else:
			return super(JSONEncoder, self).default(o)
