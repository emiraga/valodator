#!/usr/bin/env python
""" 
    Use PC^2 (Programming Contest Control) with online judges.
    Website: http://github.com/emiraga/valodator
"""

import os
import re
import sys
import time
import urllib
import httplib
import itertools
import traceback
from ConfigParser import SafeConfigParser

MAX_REFRESHES = 60 # refresh until result appears
COOKIE_FILE = './valodator_cookies'
LOG_FILE = './valodator_calls.log'
CONFIG_FILES = [ '/etc/valodator.config', './valodator.config' ]

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

def write_status(status):
    """ Show judgement to PC^2.
        We want to be able to report import/config errors to PC^2.
    """
    # status output file is supposed to be the second argument to the script
    if len(sys.argv) >= 3:
        with open(sys.argv[2], 'w') as fout:
            fout.write('<?xml version="1.0"?>\n')
            fout.write('<result outcome="' + status +'" '+
                'security="' + sys.argv[2] + '"></result>\n')# XML injection?

#Load config
PARSER = SafeConfigParser()
if not len(PARSER.read(CONFIG_FILES)):
    write_status('Error, valodator.config is not found.'+
            ' It should be in /etc/.')
    raise Exception("Config not found")

try:
    import mechanize
except ImportError, excpt:
    write_status('Error, mechanize is not installed')
    raise excpt

try:
    from BeautifulSoup import BeautifulSoup
except ImportError, excpt:
    write_status('Error, BeautifulSoup is not installed')
    raise excpt

class ValodatorException(Exception):
    """ General valodator related exception """
    pass
class RetryableException(ValodatorException):
    """ Exception which causes retry of operation """
    pass
class TooManyVerdicts(RetryableException):
    """ Too many verdicts are shown on page """
    pass
class CodeNotSubmitted(RetryableException):
    """ If web page does not show message about  successful submission """
    pass
class SubmitTooQuick(RetryableException):
    """ If web page reports that we are submitting too quick """
    pass
class WrongInputException(ValodatorException):
    """ General exception related to errors in response from server """
    pass
class ResponseTooSmall(WrongInputException):
    """ Server's response was too short """
    pass
class NoVerdictMaxRefreshes(WrongInputException):
    """ After MAX_REFRESHES there is still not verdict """
    pass
class CouldNotLogin(WrongInputException):
    """ Login failure, wrong username/password? """
    pass
class ConfigError(ValodatorException):
    """ When there is a missing entry of wrong entry in config file """
    pass
def build_browser(cookiejar):
    """ Returns a mechanize.Browser object properly configured """
    browser = mechanize.Browser(factory=mechanize.RobustFactory())
    browser.set_cookiejar(cookiejar)
    #browser.set_handle_gzip(True)
    browser.set_handle_equiv(True)
    browser.set_handle_refresh(False)
    browser.set_handle_redirect(True)
    browser.set_handle_referer(True)
    browser.set_handle_robots(False)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows '
        'NT 5.1; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10')]
    #browser.set_debug_http(True)
    if PARSER.has_section('general') and PARSER.has_option('general', 'proxy'):
        proxy = PARSER.get('general', 'proxy')
        if proxy:
            browser.set_proxies({ "http" : proxy, "https" : proxy })
    return browser

class OnlineJudge(object):
    """ Abstract class for online judge website """
    skipfile = '' # override this
    mapstatus = {
        'Accepted' : MSG_ACCEPTED,
        'Wrong' : MSG_WA,
        'Presentation' : MSG_PE,
        'Time' : MSG_TLE,
        'Memory' : MSG_MLE,
        'Runtime' : MSG_RE,
        'Crash' : MSG_RE,
        'Compile Error' : MSG_CE,
        'Compile error' : MSG_CE,
        'Compilation error' : MSG_CE,
        'Compilation Error' : MSG_CE,
        'Output' : MSG_OLE,
        'Restricted' : MSG_RESTRICT,
    }
    def __init__(self, br_):
        """ We will keep a list of id_'s which we must skip in a file """
        self.br_ = br_
        if os.access(self.skipfile, os.F_OK):
            with open(self.skipfile) as fskip:
                self.skip = [a.strip() for a in fskip]
        else:
            self.skip = [status[0] for status in self.get_status_list()]
            with open(self.skipfile, 'w') as fskip:
                fskip.write( '\n'.join(self.skip)+'\n' )
            print 'Skipfile written'

    def add_new_skip(self, id_):
        """ Add new id_ of problem which we skip """
        with open(self.skipfile, 'a') as fskip:
            fskip.write( id_ + '\n')
        # Do not add this id_ to the self.skip,
        # since we may want to retry/refresh.

    def cleanup_after_crash(self):
        """ Remove skipfiles """
        if os.access(self.skipfile, os.F_OK):
            os.remove(self.skipfile)

    def get_verdict(self, problem, language, code, retry=True):
        """ 
            Given the problem ID, language, and code; submit this solution to
            online judge and read the verdict.

            Override this method.
        """
        pass

    def get_status_list(self, skip=False, retry=True):
        """
            Read the list of IDs and statuses from website.

            Override this method.
        """
        pass

    def guess_verdict(self, status):
        """ Based on status message guess verdict from the judge """
        print 'status = "' + status + '"'
        for pattern, msg in self.mapstatus.items():
            if pattern in status:
                return msg
        return None

class LiveArchive(OnlineJudge):
    """ Online judge live archive icpc """
    submiturl = 'http://acmicpc-live-archive.uva.es/nuevoportal/mailer.php'
    skipfile = './livearchive_skip.txt'
    languages = ['C', 'C++', 'Java']

    def __init__(self, br_):
        self.userid = PARSER.get('livearchive', 'userid')
        self.staturl = ('http://acmicpc-live-archive.uva.es/nuevoportal'
                + '/status.php?u=' + self.userid)
        #Call parent contructor
        OnlineJudge.__init__(self, br_)

    def get_status_list(self, skip=False, retry=True):
        ret = []
        soup = BeautifulSoup( self.br_.open(self.staturl).read() )
        table = soup.find('table', 'ContentTable')
        for tr_ in table.findAll('tr'):
            tds = tr_.findAll('td')
            if len(tds) >= 1 and len(tds[0].contents) >= 1:
                id_ = re.search('[0-9]+', tds[0].contents[0] )
            else:
                id_ = None
            if len(tds) >= 3 and len(tds[2].contents) >= 1:
                status = str(tds[2].contents[0])
            else:
                status = None
            if id_ and status and (not skip or id_.group() not in self.skip ):
                ret.append( (id_.group(), status  ) )
        return ret

    def get_verdict(self, problem, language, code, retry=True):
        data = {
            'paso'     : 'paso', #WTF?
            'problem'  : problem,
            'userid'   : self.userid,
            'language' : self.languages[ language ],
            'code'     : code,
            'comment'  : '',
        }
        print "Submitting problem..."
        resp = self.br_.open( self.submiturl, urllib.urlencode(data) )
        if len(resp.read()) < 2000:
            raise ResponseTooSmall()
        for _ in xrange(MAX_REFRESHES):
            slist = self.get_status_list(True)
            if len(slist)>=2:
                raise TooManyVerdicts()
            if len(slist) == 1:
                (id_, status) = slist[0]
                self.add_new_skip(id_)
                guess = self.guess_verdict(status)
                if guess:
                    return guess
                print 'Unknown status: ' + status
            print '.'
            time.sleep(2)
        raise NoVerdictMaxRefreshes()

class TjuOnlineJudge(OnlineJudge):
    """ Online judge tju """
    submiturl = 'http://acm.tju.edu.cn/toj/submit_process.php'
    skipfile = './tju_skip.txt'
    languages = ['0', '1', '2'] # C, C++, Java

    def __init__(self, br_):
        self.username = PARSER.get('tju', 'username')
        self.password = PARSER.get('tju', 'password')
        self.staturl = ('http://acm.tju.edu.cn/toj/status.php?user='
                + self.username)
        #Call parent contructor
        OnlineJudge.__init__(self, br_)

    def get_status_list(self, skip=False, retry=True):
        ret = []
        soup = BeautifulSoup( self.br_.open(self.staturl).read() )
        for table in soup.findAll('table'):
            for tr_ in table.findAll('tr'):
                tds = tr_.findAll('td')
                if len(tds) >= 1 and len(tds[0].contents) >= 1:
                    id_ = re.search('[0-9]+', str(tds[0]) )
                else:
                    id_ = None
                if len(tds) >= 3 and len(tds[2].contents) >= 1:
                    status = str(tds[2].contents[0])
                else:
                    status = None
                if id_ and len(id_.group()) >= 6 and status and (
                        not skip or id_.group() not in self.skip ):
                    ret.append( (id_.group(), status  ) )
        return ret

    def get_verdict(self, problem, language, code, retry=True):
        data = {
            'prob_id'  : problem,
            'user_id'  : self.username,
            'passwd'   : self.password,
            'language' : self.languages[ language ],
            'source'   : code,
        }
        print "Submitting problem..."
        resp = self.br_.open( self.submiturl, urllib.urlencode(data) ).read()
        if len(resp) < 800:
            raise ResponseTooSmall()
        if 'submitted too quick' in resp:
            time.sleep(5)
            raise SubmitTooQuick()
        if 'code has been submitted' not in resp:
            raise CodeNotSubmitted()
        for _ in xrange(MAX_REFRESHES):
            slist = self.get_status_list(True)
            if len(slist)>=2:
                raise TooManyVerdicts()
            if len(slist) == 1:
                (id_, status) = slist[0]
                self.add_new_skip(id_)
                guess = self.guess_verdict(status)
                if guess:
                    return guess
                print 'Unknown status: ' + status
            print '.'
            time.sleep(2)
        raise NoVerdictMaxRefreshes()

class TimusOnlineJudge(OnlineJudge):
    """ Online judge timus """
    submiturl = 'http://acm.timus.ru/submit.aspx'
    skipfile = './timus_skip.txt'
    languages = ['9', '10', '7'] # C, C++, Java

    def __init__(self, br_):
        self.userid = PARSER.get('timus', 'userid')
        number = re.search('[0-9]+', self.userid )
        if not number:
            raise ConfigError()
        self.usernumber = number.group()
        self.staturl = ('http://acm.timus.ru/status.aspx?author='
                + self.usernumber)
        #Call parent contructor
        OnlineJudge.__init__(self, br_)

    def get_status_list(self, skip=False, retry=True):
        ret = []
        soup = BeautifulSoup( self.br_.open(self.staturl).read() )
        table = soup.find('table', 'status')
        for tr_ in table.findAll('tr'):
            tds = tr_.findAll('td')
            if len(tds) >= 1 and len(tds[0].contents) >= 1:
                id_ = re.search('[0-9]+', str(tds[0]) )
            else:
                id_ = None
            if len(tds) >= 6 and len(tds[5].contents) >= 1:
                status = str(tds[5])
            else:
                status = None
            if id_ and len(id_.group()) >= 6 and status and (
                    not skip or id_.group() not in self.skip ):
                ret.append( (id_.group(), status  ) )
        return ret

    def get_verdict(self, problem, language, code, retry=True):
        data = {
            'Action'    : 'submit',
            'JudgeID'   : self.userid,
            'ProblemNum': problem,
            'SpaceID'   : '1',
            'Language'  : self.languages[ language ],
            'Source'    : code,
        }
        print "Submitting problem..."
        resp = self.br_.open( self.submiturl, urllib.urlencode(data) )
        if len(resp.read()) < 800:
            raise ResponseTooSmall()
        for _ in xrange(MAX_REFRESHES):
            slist = self.get_status_list(True)
            if len(slist)>=2:
                raise TooManyVerdicts()
            if len(slist) == 1:
                (id_, status) = slist[0]
                self.add_new_skip(id_)
                guess = self.guess_verdict(status)
                if guess:
                    return guess
                print 'Unknown status: ' + status
            print '.'
            time.sleep(2)
        raise NoVerdictMaxRefreshes()

class SpojOnlineJudge(OnlineJudge):
    """ Sphere Online Judge """
    submiturl = 'http://www.spoj.pl/submit/complete/'
    skipfile = './spoj_skip.txt'
    languages = ['11', '41', '10'] # C, C++, Java
    mapstatus = {
        'accepted' : MSG_ACCEPTED,
        'wrong answer' : MSG_WA,
        'presentation' : MSG_PE,
        'time limit' : MSG_TLE,
        'memory' : MSG_MLE,
        'runtime' : MSG_RE,
        'compilation error' : MSG_CE,
        'output' : MSG_OLE,
        'restricted' : MSG_RESTRICT,
    }

    def __init__(self, br_):
        self.username = PARSER.get('spoj', 'username')
        self.password = PARSER.get('spoj', 'password')
        self.staturl = 'http://www.spoj.pl/status/' + self.username + '/'
        #Call parent contructor
        OnlineJudge.__init__(self, br_)

    def get_status_list(self, skip=False, retry=True):
        ret = []
        soup = BeautifulSoup( self.br_.open(self.staturl).read() )
        for table in soup.findAll('table', 'problems'):
            for tr_ in table.findAll('tr'):
                tds = tr_.findAll('td')
                if len(tds) >= 1 and len(tds[0].contents) >= 1:
                    id_ = re.search('[0-9]+', str(tds[0]) )
                else:
                    id_ = None
                if len(tds) >= 5 and len(tds[4].contents) >= 1:
                    status = str(tds[4])
                else:
                    status = None
                if id_ and len(id_.group()) >= 6 and status and (
                        not skip or id_.group() not in self.skip ):
                    ret.append( (id_.group(), status  ) )
        return ret

    def get_verdict(self, problem, language, code, retry=True):
        data = {
            'login_user'   : self.username,
            'password'     : self.password,
            'problemcode'  : problem,
            'lang'         : self.languages[ language ],
            'file'         : code,
            'submit'       : 'Send',
        }
        print "Submitting problem..."
        resp = self.br_.open( self.submiturl, urllib.urlencode(data) )
        if len(resp.read()) < 2000:
            raise ResponseTooSmall()
        for _ in xrange(MAX_REFRESHES):
            slist = self.get_status_list(True)
            if len(slist)>=2:
                raise TooManyVerdicts()
            if len(slist) == 1:
                (id_, status) = slist[0]
                self.add_new_skip(id_)
                guess = self.guess_verdict(status)
                if guess:
                    return guess
                print 'Unknown status: ' + status
            print '.'
            time.sleep(2)
        raise NoVerdictMaxRefreshes()

class UvaOnlineJudge(OnlineJudge):
    """ Online judge UVa """
    loginurl = 'http://uva.onlinejudge.org/'
    submiturl = ('http://uva.onlinejudge.org/index.php?'+
            'option=com_onlinejudge&Itemid=25&page=save_submission')
    staturl = ('http://uva.onlinejudge.org/'+
            'index.php?option=com_onlinejudge&Itemid=9')
    languages = ['1', '3', '2'] # C, C++, Java
    skipfile = './uva_skip.txt'

    def __init__(self, br_):
        self.username = PARSER.get('uva', 'username')
        self.password = PARSER.get('uva', 'password')
        #Call parent contructor
        OnlineJudge.__init__(self, br_)

    def login(self):
        """ Log in to the Uva website """
        print 'opening front page'
        self.br_.open(self.loginurl)
        for form in self.br_.forms():
            print form.attrs
            if 'task=login' in form.attrs['action']:
                form.name = 'login'
        self.br_.select_form('login')
        self.br_.form['username'] = self.username
        self.br_.form['passwd'] = self.password
        self.br_.form['remember'] = ['yes']
        print 'logging in...'
        self.br_.submit()

    def get_status_list(self, skip=False, retry=True):
        ret = []
        resp = self.br_.open(self.staturl)
        try:
            self.br_.find_link(text='Logout')
        except mechanize.LinkNotFoundError:
            if retry:
                self.login()
                return self.get_status_list(skip, retry=False)
            else:
                raise CouldNotLogin()
        soup = BeautifulSoup( resp.read() )
        for tr_ in itertools.chain(
                soup.findAll('tr', 'sectiontableentry1'),
                soup.findAll('tr', 'sectiontableentry2') ):
            tds = tr_.findAll('td')
            if len(tds) >= 1 and len(tds[0].contents) >= 1:
                id_ = re.search('[0-9]+', tds[0].contents[0])
            else:
                id_ = None
            if len(tds) >= 4:
                status = str(tds[3])
            else:
                status = None
            if id_ and len(id_.group()) >= 6 and status and (
                    not skip or id_.group() not in self.skip ):
                ret.append( (id_.group(), status  ) )
        return ret

    def get_verdict(self, problem, language, code, retry=True):
        data = {
            'localid'   : problem,
            'language'  : self.languages [ language ],
            'code'      : code,
        }
        print 'Submitting problem...'
        resp = self.br_.open( self.submiturl, urllib.urlencode(data) )
        try:
            self.br_.find_link(text='Logout')
        except mechanize.LinkNotFoundError:
            if retry:
                self.login()
                return self.get_verdict(problem, language, code, retry=False)
            else:
                raise CouldNotLogin()
        if len(resp.read()) < 2000:
            raise ResponseTooSmall()
        for _ in xrange(MAX_REFRESHES):
            slist = self.get_status_list(True)
            if len(slist)>=2:
                raise TooManyVerdicts()
            if len(slist) == 1:
                (id_, status) = slist[0]
                self.add_new_skip(id_)
                guess = self.guess_verdict(status)
                if guess:
                    return guess
                print 'Unknown status: ' + status
            time.sleep(2)
            print '.'
        raise NoVerdictMaxRefreshes()

def recognize_language(fname):
    """ Based on file extension, recognize language """
    if fname.endswith('.c'):
        return LANG_C
    if fname.endswith('.cpp'):
        return LANG_CPP
    if fname.endswith('.cc'):
        return LANG_CPP
    if fname.endswith('.java'):
        return LANG_JAVA
    raise Exception('Unreconized file extension')

def recognize_problem(url):
    """ Based on url, recognize website and problem """
    if not url.startswith('http'):
        spl = url.split('/')
        if len(spl) != 2:
            raise Exception('Problem code/URL is weird')
        return spl

    if url.startswith('http://acmicpc-live-archive.uva.es/'):
        id_ = re.search('[0-9]+', url)
        if not id_:
            raise Exception('Problem id_ not found')
        return 'livearchive', id_.group()

    if url.startswith('http://acm.tju.edu.cn'):
        id_ = re.search('[0-9]+', url)
        if not id_:
            raise Exception('Problem id_ not found')
        return 'tju', id_.group()

    if url.startswith('http://acm.timus.ru/'):
        id_ = re.search('num=([0-9]+)', url)
        if not id_:
            raise Exception('Problem id_ not found')
        return 'timus', id_.group(1)

    if (url.startswith('https://www.spoj.pl/') or 
            url.startswith('http://www.spoj.pl/')):
        id_ = re.search('spoj.pl/problems/([^/]+)/', url)
        if not id_:
            raise Exception('Problem id_ not found')
        return 'spoj', id_.group(1)
    return '', ''

def format_exception_info(level = 6):
    """ Returns a string with details of exception """
    error_type, error_value, trbk = sys.exc_info()
    tb_list = traceback.format_tb(trbk, level)    
    return "Error: %s \nDescription: %s \nTraceback:" % (error_type.__name__,
            error_value) + '\n'.join(tb_list)

def build_web_judge(website, browser):
    """ Build a derived OnlineJudge object """
    if website == 'livearchive' or website == 'live-archive' or website == 'la':
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
        raise Exception('Website not recognized')
    return web

def main():
    """ Program's entry point """
    try:
        web = None
        if len(sys.argv) < 4:
            print "Usage: " + sys.argv[0] + " code.ext out.xml website/problem"
            print
            print "ext = c | cpp | cc | java"
            print "website = livearchive | uva | tju | timus | spoj"
            print
            write_status('Too few arguments to valodator.py')
            sys.exit(1)

        with open(sys.argv[1]) as fcode:
            code = fcode.read()
        url = sys.argv[3]

        website, problem = recognize_problem(url)
        website = website.lower()
        language = recognize_language(sys.argv[1])

        cjar = mechanize.LWPCookieJar()
        if os.access(COOKIE_FILE, os.F_OK):
            cjar.load(COOKIE_FILE)

        # some weird exception pops up due to server's error,
        # and sometimes we get RetryableException
        for retry in xrange(10):
            try:
                browser = build_browser(cjar)
                print 'Website is ' + website
                web = build_web_judge(website, browser)
                status = web.get_verdict(problem, language, code)
                break
            except (httplib.HTTPException, RetryableException):
                web.cleanup_after_crash()
                stack = format_exception_info()
                print stack
                with open(LOG_FILE, 'a') as flog:
                    flog.write('Exception: ' + stack + '\n' )
                if retry == 9:
                    write_status("Error, too many retryables.")
                    sys.exit(1)
                time.sleep(2)

        cjar.save(COOKIE_FILE, ignore_discard=True, ignore_expires=True )
        write_status(status)
    except Exception, exc: #gotta catch 'em all, for logging purposes
        if web:
            web.cleanup_after_crash()
        stack = format_exception_info()
        print stack
        with open(LOG_FILE, 'a') as flog:
            flog.write('Exception: ' + stack + '\n' )
        write_status(str(type(exc)) + " " + str(exc))

if __name__ == '__main__':
    main()

