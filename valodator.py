#!/usr/bin/env python
# from http://github.com/emiraga/valodator

import sys
import os
import re
import time
import itertools
import traceback
import cookielib
import urllib
import httplib
from ConfigParser import SafeConfigParser

import warnings
warnings.filterwarnings('ignore', '.*',)

MAX_REFRESHES = 15 # refresh until result appears
COOKIE_FILE = './valodator_cookies'
LOG_FILE = './valodator_calls.log'

parser = SafeConfigParser()
config_files = [ '/etc/valodator.config', './valodator.config' ]
parser.read(config_files)

# From PC^2, and live-archive
MSG_ACCEPTED = 'accepted'
MSG_WA = 'No - Wrong Answer'
MSG_RE = 'No - Runtime Error'
MSG_TLE = 'No - Time-limit Exceeded'
MSG_PE = 'No - Presentation Error'
MSG_CE = 'No - Compilation Error'
MSG_MLE = 'No - Memory-limit Exceeded'
MSG_OLE = 'No - Output-limit Exceeded'
MSG_RESTRICT = 'No - Restricted Function'
MSG_INDET = 'No - Indeterminant'
MSG_OTHER = 'No - Other - Contact Staff'

# Don't change this
LANG_C = 0
LANG_CPP = 1
LANG_JAVA = 2

def write_status(outputfile, status):
	""" Show judgement to PC^2.
		We want to be able to report import errors to PC^2.
	"""
	with open(outputfile, 'w') as f:
		f.write('<?xml version="1.0"?>\n');
		f.write('<result outcome="' + status +'" '
				+'security="' + outputfile + '"></result>\n')

try:
	import mechanize
except ImportError, e:
	if len(sys.argv) >= 3:
		write_status(sys.argv[2], 'Error, mechanize is not installed')
	raise e

try:
	from BeautifulSoup import BeautifulSoup
except ImportError, e:
	if len(sys.argv) >= 3:
		write_status(sys.argv[2], 'Error, BeautifulSoup is not installed')
	raise e

def BuildBrowser(cj):
	br = mechanize.Browser(factory=mechanize.RobustFactory())
	br.set_cookiejar(cj)
	#br.set_handle_gzip(True)
	br.set_handle_equiv(True)
	br.set_handle_refresh(False)
	br.set_handle_redirect(True)
	br.set_handle_referer(True)
	br.set_handle_robots(False)
	br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1;'
		' en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10')]
	#br.set_debug_http(True)
	return br

class OnlineJudge(object):
	def __init__(self, br):
		""" We will keep a list of ID's which we must skip in a file"""
		self.br = br
		if os.access(self.skipfile, os.F_OK):
			with open(self.skipfile) as f:
				self.skip = [a.strip() for a in f]
		else:
			self.skip = [ID for ID,status in self.getStatusList()]
			with open(self.skipfile,'w') as f:
				f.write( '\n'.join(self.skip)+'\n' )
			print 'Skip file written'

	def add_new_skip(self, ID):
		""" Add new ID of problem which we skip """
		with open(self.skipfile,'a') as f: f.write( ID + '\n')

	def cleanup_after_crash(self):
		""" Remove skip files """
		if os.access(self.skipfile, os.F_OK):
			os.remove(self.skipfile)

class LiveArchive(OnlineJudge):
	userid = parser.get('livearchive', 'userid')
	staturl = ('http://acmicpc-live-archive.uva.es/nuevoportal/status.php?u='+
		userid)
	submiturl = 'http://acmicpc-live-archive.uva.es/nuevoportal/mailer.php'
	skipfile = './livearchive_skip.txt'
	languages = ['C', 'C++', 'Java']

	def __init__(self, br):
		OnlineJudge.__init__(self, br)

	def getStatusList(self, skip = False):
		ret = []
		s = BeautifulSoup( self.br.open(self.staturl).read() )
		table = s.find('table','ContentTable')
		for tr in table.findAll('tr'):
			tds = tr.findAll('td')
			if len(tds) >= 1 and len(tds[0].contents) >= 1:
				ID = re.search('[0-9]+', tds[0].contents[0] )
			else:
				ID = None
			if len(tds) >= 3 and len(tds[2].contents) >= 1:
				status = str(tds[2].contents[0])
			else:
				status = None
			if ID and status and (not skip or ID.group() not in self.skip ):
				ret.append( (ID.group(), status  ) )
		return ret

	def getVerdict(self, problem, language, code):
		data = {
			'paso'     : 'paso', #WTF?
			'problem'  : problem,
			'userid'   : self.userid,
			'language' : self.languages[ language ],
			'code'     : code,
			'comment'  : '',
		}
		resp = self.br.open( self.submiturl, urllib.urlencode(data) )
		if len(resp.read()) < 2000:	raise Exception('Response was too small')
		for x in xrange(MAX_REFRESHES):
			l = self.getStatusList(True)
			if len(l)>=2: raise Exception('More than one status response found')
			if len(l) == 1:
				(ID,status) = l[0]
				self.add_new_skip(ID)

				if 'Accepted' in status: return MSG_ACCEPTED
				if 'Wrong' in status: return MSG_WA
				if 'Presentation' in status: return MSG_PE
				if 'Time' in status: return MSG_TLE
				if 'Memory' in status: return MSG_MLE
				if 'Runtime' in status: return MSG_RE
				if 'Compil' in status: return MSG_CE
				if 'Output' in status: return MSG_OLE
				if 'Restricted' in status: return MSG_RESTRICT
				print 'Unknown status: ' + status
			print '.'
			time.sleep(1)
		raise Exception('Status response did not arrive after many retries')

class TjuOnlineJudge(OnlineJudge):
	username = parser.get('tju','username')
	password = parser.get('tju','password')
	staturl = 'http://acm.tju.edu.cn/toj/status.php?user=' + username
	submiturl = 'http://acm.tju.edu.cn/toj/submit_process.php'
	skipfile = './tju_skip.txt'
	languages = ['0', '1', '2'] # C, C++, Java

	def __init__(self, br):
		OnlineJudge.__init__(self, br)

	def getStatusList(self, skip = False):
		ret = []
		s = BeautifulSoup( self.br.open(self.staturl).read() )
		for table in s.findAll('table'):
			for tr in table.findAll('tr'):
				tds = tr.findAll('td')
				if len(tds) >= 1 and len(tds[0].contents) >= 1:
					ID = re.search('[0-9]+', str(tds[0]) )
				else:
					ID = None
				if len(tds) >= 3 and len(tds[2].contents) >= 1:
					status = str(tds[2].contents[0])
				else:
					status = None
				if ID and len(ID.group()) >= 6 and status and (
						not skip or ID.group() not in self.skip ):
					ret.append( (ID.group(), status  ) )
		return ret

	def getVerdict(self, problem, language, code):
		data = {
			'prob_id'  : problem,
			'user_id'   : self.username,
			'passwd'   : self.password,
			'language' : self.languages[ language ],
			'source'   : code,
		}
		resp = self.br.open( self.submiturl, urllib.urlencode(data) )
		if len(resp.read()) < 800:	raise Exception('Response was too small')
		for x in xrange(MAX_REFRESHES):
			l = self.getStatusList(True)
			if len(l)>=2: raise Exception('More than one status response found')
			if len(l) == 1:
				(ID,status) = l[0]
				self.add_new_skip(ID)
				if 'Accepted' in status: return MSG_ACCEPTED
				if 'Wrong' in status: return MSG_WA
				if 'Presentation' in status: return MSG_PE
				if 'Time' in status: return MSG_TLE
				if 'Memory' in status: return MSG_MLE
				if 'Runtime' in status: return MSG_RE
				if 'Compil' in status: return MSG_CE
				if 'Output' in status: return MSG_OLE
				if 'Restricted' in status: return MSG_RESTRICT
				print 'Unknown status: ' + status
			print '.'
			time.sleep(1)
		raise Exception('Status response did not arrive after many retries')

class TimusOnlineJudge(OnlineJudge):
	userid = parser.get('timus','userid')
	usernumber = parser.get('timus','usernumber')
	staturl = 'http://acm.timus.ru/status.aspx?author='+usernumber
	submiturl = 'http://acm.timus.ru/submit.aspx'
	skipfile = './timus_skip.txt'
	languages = ['9', '10', '7'] # C, C++, Java

	def __init__(self, br):
		OnlineJudge.__init__(self, br)

	def getStatusList(self, skip = False):
		ret = []
		s = BeautifulSoup( self.br.open(self.staturl).read() )
		table = s.find('table','status')
		for tr in table.findAll('tr'):
			tds = tr.findAll('td')
			if len(tds) >= 1 and len(tds[0].contents) >= 1:
				ID = re.search('[0-9]+', str(tds[0]) )
			else:
				ID = None
			if len(tds) >= 6 and len(tds[5].contents) >= 1:
				status = str(tds[5])
			else:
				status = None
			if ID and len(ID.group()) >= 6 and status and (
					not skip or ID.group() not in self.skip ):
				ret.append( (ID.group(), status  ) )
		return ret

	def getVerdict(self, problem, language, code):
		data = {
			'Action'    : 'submit',
			'JudgeID'   : self.userid,
			'ProblemNum': problem,
			'SpaceID'   : '1',
			'Language'  : self.languages[ language ],
			'Source'    : code,
		}
		resp = self.br.open( self.submiturl, urllib.urlencode(data) )
		if len(resp.read()) < 800:	raise Exception('Response was too small')
		for x in xrange(MAX_REFRESHES):
			l = self.getStatusList(True)
			if len(l)>=2: raise Exception('More than one status response found')
			if len(l) == 1:
				(ID,status) = l[0]
				self.add_new_skip(ID)
				if 'Accepted' in status: return MSG_ACCEPTED
				if 'Wrong' in status: return MSG_WA
				if 'Presentation' in status: return MSG_PE
				if 'Time' in status: return MSG_TLE
				if 'Memory' in status: return MSG_MLE
				if 'Runtime' in status or 'Crash' in status: return MSG_RE
				if 'Compil' in status: return MSG_CE
				if 'Output' in status: return MSG_OLE
				if 'Restricted' in status: return MSG_RESTRICT
				print 'Unknown status: ' + status
			print '.'
			time.sleep(1)
		raise Exception('Status response did not arrive after many retries')

class SpojOnlineJudge(OnlineJudge):
	username = parser.get('spoj','username')
	password = parser.get('spoj','password')
	staturl = 'http://www.spoj.pl/status/'+username+'/'
	submiturl = 'http://www.spoj.pl/submit/complete/'
	skipfile = './spoj_skip.txt'
	languages = ['11', '41', '10'] # C, C++, Java

	def __init__(self, br):
		OnlineJudge.__init__(self, br)

	def getStatusList(self, skip = False):
		ret = []
		s = BeautifulSoup( self.br.open(self.staturl).read() )
		for table in s.findAll('table','problems'):
			for tr in table.findAll('tr'):
				tds = tr.findAll('td')
				if len(tds) >= 1 and len(tds[0].contents) >= 1:
					ID = re.search('[0-9]+', str(tds[0]) )
				else:
					ID = None
				if len(tds) >= 5 and len(tds[4].contents) >= 1:
					status = str(tds[4])
				else:
					status = None
				if ID and len(ID.group()) >= 6 and status and (
						not skip or ID.group() not in self.skip ):
					ret.append( (ID.group(), status  ) )
		return ret

	def getVerdict(self, problem, language, code):
		data = {
			'login_user'   : self.username,
			'password'     : self.password,
			'problemcode'  : problem,
			'lang'         : self.languages[ language ],
			'file'         : code,
			'submit'       : 'Send',
		}
		resp = self.br.open( self.submiturl, urllib.urlencode(data) )
		if len(resp.read()) < 2000: raise Exception('Response was too small')
		for x in xrange(MAX_REFRESHES):
			l = self.getStatusList(True)
			if len(l)>=2: raise Exception('More than one status response found')
			if len(l) == 1:
				(ID,status) = l[0]
				self.add_new_skip(ID)
				if 'accepted' in status: return MSG_ACCEPTED
				if 'wrong answer' in status: return MSG_WA
				if 'presentation' in status: return MSG_PE
				if 'time limit' in status: return MSG_TLE
				if 'memory' in status: return MSG_MLE
				if 'runtime' in status: return MSG_RE
				if 'compilation' in status: return MSG_CE
				if 'output' in status: return MSG_OLE
				if 'restricted' in status: return MSG_RESTRICT
				print 'Unknown status: ' + status
			print '.'
			time.sleep(1)
		raise Exception('Status response did not arrive after many retries')

class UvaOnlineJudge(OnlineJudge):
	username = parser.get('uva','username')
	password = parser.get('uva','password')
	loginurl = 'http://uva.onlinejudge.org/'
	submiturl = ('http://uva.onlinejudge.org/index.php?'+
			'option=com_onlinejudge&Itemid=25&page=save_submission')
	staturl = ('http://uva.onlinejudge.org/'+
			'index.php?option=com_onlinejudge&Itemid=9')
	languages = ['1', '3', '2'] # C, C++, Java
	skipfile = './uva_skip.txt'

	def __init__(self, br):
		OnlineJudge.__init__(self, br)

	def login(self):
		print 'opening front page'
		self.br.open(self.loginurl)
		for f in self.br.forms():
			print f.attrs
			if 'task=login' in f.attrs['action']:
				f.name='login'
		self.br.select_form('login')
		self.br.form['username'] = self.username
		self.br.form['passwd'] = self.password
		self.br.form['remember'] = ['yes']
		print 'logging in '
		self.br.submit()

	def getStatusList(self, skip = False, retry=True):
		ret = []
		resp = self.br.open(self.staturl)
		try:
			self.br.find_link(text='Logout')
		except mechanize.LinkNotFoundError:
			if retry:
				self.login()
				return self.getStatusList(skip, retry=False)
			else:
				raise Exception('Username/Password or something else is wrong')
		s = BeautifulSoup( resp.read() )
		for tr in itertools.chain(
				s.findAll('tr','sectiontableentry1'),
				s.findAll('tr','sectiontableentry2') ):
			tds=tr.findAll('td')
			if len(tds) >= 1 and len(tds[0].contents) >= 1:
				ID = re.search('[0-9]+', tds[0].contents[0])
			else:
				ID = None
			if len(tds) >= 4:
				status = str(tds[3])
			else:
				status = None
			if ID and len(ID.group()) >= 6 and status and (
					not skip or ID.group() not in self.skip ):
				ret.append( (ID.group(), status  ) )
		return ret

	def getVerdict(self, problem, language, code, retry=True):
		data = {
			'localid'   : problem,
			'language'  : self.languages [ language ],
			'code'      : code,
		}
		print 'Submitting problem'
		resp = self.br.open( self.submiturl, urllib.urlencode(data) )
		try:
			self.br.find_link(text='Logout')
		except mechanize.LinkNotFoundError:
			if retry:
				self.login()
				return self.getVerdict(problem, language, code, retry=False)
			else:
				raise Exception('Username/Password or something else is wrong')
		if len(resp.read()) < 2000:	raise Exception('Response was too small')
		for x in xrange(MAX_REFRESHES):
			l = self.getStatusList(True)
			if len(l)>=2: raise Exception('More than one status response found')
			if len(l) == 1:
				(ID,status) = l[0]
				self.add_new_skip(ID)
				if 'Accepted' in status: return MSG_ACCEPTED
				if 'Wrong' in status: return MSG_WA
				if 'Presentation' in status: return MSG_PE
				if 'Time' in status: return MSG_TLE
				if 'Memory' in status: return MSG_MLE
				if 'Runtime' in status: return MSG_RE
				if 'Compil' in status: return MSG_CE
				if 'Output' in status: return MSG_OLE
				if 'Restricted' in status: return MSG_RESTRICT
				print 'Unknown status: ' + status
			time.sleep(1)
			print '.'
		raise Exception('Status response did not arrive after many retries')

def recognize_language(fname):
	if fname.endswith('.c'): return LANG_C
	if fname.endswith('.cpp'): return LANG_CPP
	if fname.endswith('.java'): return LANG_JAVA
	raise Exception('Unreconized file extension')

def recognize_url(url):
	if not url.startswith('http'):
		s = url.split('/')
		if len(s) != 2:
			raise Exception('Problem code/URL is weird')
		return s
	if url.startswith('http://acmicpc-live-archive.uva.es/'):
		ID = re.search('[0-9]+', url)
		if not ID: raise Exception('Problem ID not found')
		return 'livearchive', ID.group()
	if url.startswith('http://acm.tju.edu.cn'):
		ID = re.search('[0-9]+', url)
		if not ID: raise Exception('Problem ID not found')
		return 'tju', ID.group()
	if url.startswith('http://acm.timus.ru/'):
		ID = re.search('num=([0-9]+)', url)
		if not ID: raise Exception('Problem ID not found')
		return 'timus', ID.group(1)
	if (url.startswith('https://www.spoj.pl/') or 
			url.startswith('http://www.spoj.pl/')):
		ID = re.search('spoj.pl/problems/([^/]+)/')
		if not ID: raise Exception('Problem ID not found')
		return 'spoj', ID.group(1)
	return '',''

def formatExceptionInfo(level = 6):
	error_type, error_value, trbk = sys.exc_info()
	tb_list = traceback.format_tb(trbk, level)    
	return "Error: %s \nDescription: %s \nTraceback:" % (error_type.__name__,
			error_value) + '\n'.join(tb_list)

if __name__ == '__main__':
	with open(LOG_FILE,'a') as f:
		f.write('Called:')
		for arg in sys.argv:
			f.write(' '+arg)
		f.write('\n')
	print 'valodator running...'

	try:
		if len(sys.argv) < 4: raise Exception('Too few arguments')

		with open(sys.argv[1]) as f: code = f.read()
		outputfile = sys.argv[2]
		url = sys.argv[3]

		website, problem = recognize_url(url)
		website = website.lower()
		language = recognize_language(sys.argv[1])

		cjar = mechanize.LWPCookieJar()
		if os.access(COOKIE_FILE, os.F_OK): cjar.load(COOKIE_FILE)

		# some weird exception pops up due to server's error
		for retry in xrange(10): 
			try:
				browser = BuildBrowser(cjar)
				print 'Website is ' + website
				if website == 'livearchive' or website == 'live-archive':
					web = LiveArchive(browser)
				elif website == 'uva':
					web = UvaOnlineJudge(browser)
				elif website == 'tju':
					web = TjuOnlineJudge(browser)
				elif website == 'timus':
					web = TimusOnlineJudge(browser)
				elif website == 'spoj':
					web = SpojOnlineJudge(browser)
				else:
					raise Exception('Website not recognized');
				status = web.getVerdict(problem, language, code)
				break
			except httplib.HTTPException, e: #BadStatusLine, IncompleteRead
				web.cleanup_after_crash()
				s = formatExceptionInfo()
				print s
				with open(LOG_FILE, 'a') as f:
					f.write('Exception: ' + s + '\n' )
				if retry == 9:
					write_status(outputfile, "Error, many HTTPExceptions")
					sys.exit(1)

		cjar.save(COOKIE_FILE, ignore_discard=True, ignore_expires=True )
		write_status(outputfile, status)
	except Exception, e: #gotta catch 'em all
		s = formatExceptionInfo()
		print s
		with open(LOG_FILE, 'a') as f:
			f.write('Exception: ' + s + '\n' )
		write_status(outputfile, "Exception: " + str(e))

