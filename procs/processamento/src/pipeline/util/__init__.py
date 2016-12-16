import re
UTM_TAGS = ( 
	u'utm_source',
	u'utm_medium',
	u'utm_term',
	u'utm_content',
	u'utm_campaign'
	)   

utm_re = re.compile(u''.join((
	u'(^|&(amp;)?)(',	# either at start or preceeded by '&' or '&amp;'
	u'|'.join(UTM_TAGS),   # all tags as alternatives
	u'=)[^&]*'		 # followed by '=' and all chars upto next '&'
	))) 

def unUTM(url):
	''' Remove parametros relacionados ao Google Analytics para campanhas. Esses parametros atrapalham a identificacao da URL '''
	# check if the URL is parameterized
	if '?' in url:
		(url, params) = url.split('?', 1)
		params = utm_re.sub(u'', params)
		if '' != params:
			params = re.compile(u'^&(amp;)?').sub(u'', params)
			url = u'?'.join((url, params))
	return(url)
