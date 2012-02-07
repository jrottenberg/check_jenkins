#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

https://launchpad.net/python-jenkins
https://wiki.jenkins-ci.org/display/JENKINS/Remote+access+API
http://nagiosplug.sourceforge.net/developer-guidelines.html


Few doctests, run with :
 $ python -m doctest check_jenkins_lsb.py -v

"""
__author__ = 'Julien Rottenberg'
__date__ = "December 2011"

__version__ = "1.0"
__credits__ = """https://launchpad.net/python-jenkins - this code is a trimmed
down version with nagios specific code"""


from datetime import timedelta, datetime

from optparse import OptionParser, OptionGroup


import base64
import urllib2
import re
from urllib2 import HTTPError, URLError
from urllib import quote
from socket import setdefaulttimeout


def get_data(url, username, password, timeout):
    """
    Initialize the connection to Jenkins
    Fetch data using the api
    """

    request = urllib2.Request(url)
    if (username and password):
        b64string = base64.encodestring('%s:%s' % (username, password))
        request.add_header("Authorization", "Basic %s" % b64string)

    try:
        setdefaulttimeout(timeout)
        return urllib2.urlopen(request).read()
    except HTTPError:
        print 'CRITICAL: %s does the job ever ran successfully ?' % url
        raise SystemExit, 2
    except URLError:
        print 'CRITICAL: Error on %s Double check the server name' % url
        raise SystemExit, 2



def convert_to_timedelta(time_val):
    """
    http://code.activestate.com/recipes/577894/

    Given a *time_val* (string) such as '5d', returns a timedelta object
    representing the given value (e.g. timedelta(days=5)).  Accepts the
    following '<num><char>' formats:
    
    =========   ======= ===================
    Character   Meaning Example
    =========   ======= ===================
    s           Seconds '60s' -> 60 Seconds
    m           Minutes '5m'  -> 5 Minutes (* Default if no letter given)
    h           Hours   '24h' -> 24 Hours
    d           Days    '7d'  -> 7 Days
    =========   ======= ===================

    Examples:

    >>> convert_to_timedelta('7d')
    datetime.timedelta(7)
    >>> convert_to_timedelta('24h')
    datetime.timedelta(1)
    >>> convert_to_timedelta('60m')
    datetime.timedelta(0, 3600)
    >>> convert_to_timedelta('120s')
    datetime.timedelta(0, 120)
    >>> convert_to_timedelta('1')
    datetime.timedelta(0, 60)
    >>> convert_to_timedelta('42X')
    Traceback (most recent call last):
        ...
    ValueError: Please use a valid unit
    """
    try:
        value, unit = re.match(r'(\d+)([smhd])', time_val).groups()
        if (unit == 's'):
            return timedelta(seconds=int(value))
        elif (unit == 'm'):
            return timedelta(minutes=int(value))
        elif (unit == 'h'):
            return timedelta(hours=int(value))
        elif (unit == 'd'):
            return timedelta(days=int(value))
    except AttributeError:
        try:
            # Let's see if the user input was just the ''minutes'
            new_time_val = int(time_val)
            return convert_to_timedelta('%sm' % new_time_val)
        except ValueError:
            raise ValueError('Please use a valid unit')

    
def seconds2human(my_time):
    """ Convert given duration in seconds into human readable string

    >>> seconds2human(60)
    '0:01:00'

    >>> seconds2human(300)
    '0:05:00'

    >>> seconds2human(3601)
    '1:00:01'

    >>> seconds2human(86401)
    '1 day, 0:00:01'

    """
    time_delta = timedelta(seconds=my_time)
    return str(time_delta)



def build_url(job_url_id, suffix):
    """ Build a generic jenkins url
    based on the url of a specific Build (job/NAME/ID/)
    
    >>> build_url('https://localhost:8080/jenkins/job/myBuild/42/', '/api')
    'https://localhost:8080/jenkins/job/myBuild/api'
    
    """
    url_prefix = re.match(r'^(.*)\/\d+\/', job_url_id).group(1) 
    return url_prefix + suffix 
    
    

def check_result(params, server):
    """ From the server response and input parameter
        check if the job status should trigger an alert

    Jenkins results
    http://javadoc.jenkins-ci.org/hudson/model/Result.html


    >>> in_p = {'job': 'test', 'warning': '10d', 'critical': '42d', 'now': datetime(2012, 2, 6, 16, 10, 1)}

    >>> check_result(in_p,  {'building': True, 'result': '', 'building': True, 'timestamp': '1328573400000', 'url': 'http://localhost/job/test/6/'})
    ('OK', 'test last successful run was 0:00:01 ago - see http://localhost/job/test/buildTimeTrend')


    >>> check_result(in_p,  {'building': True, 'result': '', 'building': True, 'timestamp': '1326067800000', 'url': 'http://localhost/job/test/6/'})
    ('WARNING', 'test last successful run was 29 days, 0:00:01 ago - see http://localhost/job/test/buildTimeTrend')


    >>> check_result(in_p,  {'building': True, 'result': '', 'building': True, 'timestamp': '1297037400000', 'url': 'http://localhost/job/test/6/'})
    ('CRITICAL', 'test last successful run was 365 days, 0:00:01 ago - see http://localhost/job/test/buildTimeTrend')

    """

    job_started = datetime.fromtimestamp(int(server['timestamp'])/1000)
    now = params['now']
    now_since_start = now - job_started
    msg = '%s last successful run was %s ago - see %s' % (
                    params['job'],
                    now_since_start,
                    build_url(server['url'], '/buildTimeTrend'))

    if (now_since_start >= convert_to_timedelta(params['critical'])):
        status = 'CRITICAL'
    elif (now_since_start >= convert_to_timedelta(params['warning'])):

        status = 'WARNING'
    else:
        status = 'OK'

    return(status, msg)


def usage():
    """
    Return usage text so it can be used on failed human interactions
    """
    
    usage_string = """
    usage: %prog [options] -H SERVER -j JOB -w WARNING -c CRITICAL

    Make sure the last job is successful
             OR the current is not stuck (LastBuild)
    Warning and Critical are defined in minutes

    Ex :

    check_jenkins_lsb.py -H ci.jenkins-ci.org -j infa_release.rss -w 10 -c 42
    will check if the the job infa_release.rss is successful (or not stuck)

    """
    return usage_string
    

def controller():
    """
    Parse user input, fail quick if not enough parameters
    """

    description = """A Nagios plugin to check if the last successful
run of a Jenkins Job was not too long ago."""

    
    version = "%prog " + __version__
    parser = OptionParser(description=description, usage=usage(),
                            version=version)
    parser.set_defaults(verbose=False)



    parser.add_option('-H', '--hostname', type='string',
                        help='Jenkins hostname')

    parser.add_option('-w', '--warning', type='string',
                        help='Warning threshold, units s, m, h, d')

    parser.add_option('-c', '--critical', type='string',
                        help='Critical threshold, units s, m, h, d')


    parser.add_option('-j', '--job', type='string',
                        help='Job, use quotes if it contains space')


    connection = OptionGroup(parser, "Connection Options",
                    "Network / Authentication related options")
    connection.add_option('-u', '--username', type='string',
                        help='Jenkins username')
    connection.add_option('-p', '--password', type='string',
                        help='Jenkins password')
    connection.add_option('-t', '--timeout', type='int', default=10,
                        help='Connection timeout in seconds')
    connection.add_option('-P', '--port', type='int',
                        help='Jenkins port',
                        default=80)
    connection.add_option('--prefix', type='string',
                        help='Jenkins prefix, if not installed on /',
                        default='/')
    connection.add_option('-S', '--ssl', action="store_true",
                        default=False,
                        help='If the connection requires ssl')
    parser.add_option_group(connection)

    extra = OptionGroup(parser, "Extra Options")
    extra.add_option('-v', action='store_true', dest='verbose',
                        default=False,
                        help='Verbose mode')
    parser.add_option_group(extra)

    options, arguments = parser.parse_args()

    if (arguments != []):
        print """Non recognized option %s
        Please use --help for usage""" % arguments
        print usage()
        raise SystemExit, 2

    if (options.hostname == None):
        print "-H HOSTNAME"
        print "We need the jenkins server hostname to connect to"
        print usage()
        raise SystemExit, 2

    if (options.job == None):
        print "\n-j JOB"
        print "\nWe need the name of the job to check its health"
        print usage()
        raise SystemExit, 2

    if (options.warning == None):
        print "\n-w "
        print "\nHow long since the last successful build for a warning ?"
        print "ex: 3h or 180m or 10800s - default unit is minutes "
        print usage()
        raise SystemExit, 2

    if (options.critical == None):
        print "\n-c "
        print "\nHow long since the last successful build for a critical ?"
        print "ex: 4h or 240m or 14400s - default unit is minutes "
        print usage()
        raise SystemExit, 2

    return vars(options)


def main():
    """Runs all the functions"""

    # Command Line Parameters
    user_in = controller()



    if user_in['verbose']:
        def verboseprint(*args):
            """ http://stackoverflow.com/a/5980173 print only when verbose ON"""
            # Print each argument separately so caller doesn't need to
            # stuff everything to be printed into a single string
            print
            for arg in args:
                print arg,
            print
    else:
        verboseprint = lambda *a: None      # do-nothing function


    # Validate the port based on the required protocol
    if user_in['ssl']:
        protocol = "https"
        # Unspecified port will be 80 by default, not correct if ssl is ON
        if (user_in['port'] == 80):
            user_in['port'] = 443
    else:
        protocol = "http"

    # Let's avoid the double / if we specified a prefix
    if (user_in['prefix'] != '/'):
        user_in['prefix'] = '/%s/' %  user_in['prefix']

    user_in['url'] = "%s://%s:%s%sjob/%s/%s" % (protocol,
                        user_in['hostname'],
                        user_in['port'],
                        user_in['prefix'],
                        quote(user_in['job']),
                        'lastSuccessfulBuild/api/python')

    # Get the current time, no need to get the microseconds
    user_in['now'] = datetime.now().replace(microsecond=0)

    verboseprint("CLI Arguments : ", user_in)

    jenkins_out = eval(get_data(user_in['url'], 
                        user_in['username'], 
                        user_in['password'],
                        user_in['timeout']))

    verboseprint("Reply from server :", jenkins_out)


    status, message =  check_result(user_in, jenkins_out)

    print '%s - %s' % (status, message)
    # Exit statuses recognized by Nagios
    if   status == 'OK':
        raise SystemExit, 0
    elif status == 'WARNING':
        raise SystemExit, 1
    elif status == 'CRITICAL':
        raise SystemExit, 2
    else:
        raise SystemExit, 3


if __name__ == '__main__':
    main()

