#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

https://launchpad.net/python-jenkins
https://wiki.jenkins-ci.org/display/JENKINS/Remote+access+API
http://nagiosplug.sourceforge.net/developer-guidelines.html


Few doctests, run with :
 $ python -m doctest check_jenkins_lastSuccessfulBuild.py -v

"""
__author__ = 'Julien Rottenberg'
__date__ = "December 2011"

__version__ = "1.0"
__credits__ = """https://launchpad.net/python-jenkins - this code is a trimmed
down version with nagios specific code"""


from datetime import timedelta

from optparse import OptionParser, OptionGroup

from time import strftime, gmtime, time
import base64
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote
from socket import setdefaulttimeout


def get_data(url, username, password, timeout):
    """Initialize the connection to Jenkins"""

    request = urllib2.Request(url)
    if (username and password):
        base64string = base64.encodestring('%s:%s' % (username, password))
        request.add_header("Authorization", "Basic %s" % base64string)

    try:
        setdefaulttimeout(timeout)
        return urllib2.urlopen(request).read()
    except HTTPError:
        print 'CRITICAL: Error on %s does the job exist or ever ran successfully ?' % url
        raise SystemExit, 2
    except URLError:
        print 'CRITICAL:Error on %s Double check the server name' % url
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
    m           Minutes '5m'  -> 5 Minutes (* Default if no letter passed)
    h           Hours   '24h' -> 24 Hours
    d           Days    '7d'  -> 7 Days
    =========   ======= ===================

    Examples::

        >>> convert_to_timedelta('7d')
        datetime.timedelta(7)
        >>> convert_to_timedelta('24h')
        datetime.timedelta(1)
        >>> convert_to_timedelta('60m')
        datetime.timedelta(0, 3600)
        >>> convert_to_timedelta('120s')
        datetime.timedelta(0, 120)
        >>> convert_to_timedelta('120')
        datetime.timedelta(0, 7200)
    """
    num = int(time_val[:-1])
    if time_val.endswith('s'):
        return timedelta(seconds=num)
    elif time_val.endswith('m'):
        return timedelta(minutes=num)
    elif time_val.endswith('h'):
        return timedelta(hours=num)
    elif time_val.endswith('d'):
        return timedelta(days=num)
    else:
        return convert_to_timedelta('%sm' % time_val)

def seconds2human(my_time):
    """ Convert given seconds into human readable string

    >>> seconds2human(60)
    '00:01:00'

    >>> seconds2human(300)
    '00:05:00'

    >>> seconds2human(3601)
    '01:00:01'

    >>> seconds2human(86401)
    '1 day, 00:00:01'

    """
    my_days, my_seconds = divmod(my_time, 86400)
    time_delta = timedelta(seconds=my_seconds)
    reminder = strftime("%H:%M:%S", gmtime(time_delta.seconds))
    if my_days > 1:
        return "%s days, %s" % (my_days, reminder)
    elif my_days == 1:
        return "%s day, %s" % (my_days, reminder)
    else:
        return strftime("%H:%M:%S", gmtime(time_delta.seconds))



def check_result(params, server):
    """ From the server response and input parameter
        check if the job status should trigger an alert

    Jenkins results
    http://javadoc.jenkins-ci.org/hudson/model/Result.html


    >>> in_p = {'job': 'test', 'warning': 10, 'critical': 42}

    >>> check_result(in_p, {'building': False, 'result': 'SUCCESS', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
    ('OK', 'test exited normally after 00:00:17')


    >>> check_result(in_p,  {'building': False, 'result': 'UNSTABLE', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
    ('WARNING', 'test is marked as unstable after 00:00:17, see http://localhost/job/test/6/console#footer')


    >>> check_result(in_p, {'building': False, 'result': 'FAILURE', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
    ('CRITICAL', 'test exited with an error, see http://localhost/job/test/6/console#footer')


    >>> check_result(in_p, {'building': False, 'result': 'ABORTED', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
    ('UNKNOWN', 'test has been aborted, see http://localhost/job/test/6/console#footer')


    # Tricky, as the test is time dependant... try it with timestmap value in
    # > import time; int(time.time())*1000
    # > import time; int(time.time())*1000 - 10*60*1000
    # > import time; int(time.time())*1000 - 42*60*1000
    >>> check_result(in_p,  {'building': True, 'result': '', 'building': True, 'timestamp': '1324261160000', 'url': 'http://localhost/job/test/6/'})
    ('CRITICAL', 'test still running after 12:55:30, see http://localhost/job/test/6/console#footer')

    """

    job_started = int(server['timestamp'])/1000
    now = params['now']
    now_since_start = timedelta(seconds=now - job_started)
    days_since_start = now_since_start.days
    print days_since_start
    s2h_since_start = seconds2human(now_since_start.seconds)
    print now_since_start

    if (now_since_start >= convert_to_timedelta(params['critical'])):
        msg = '%s last successful run was %s ago - see %s../buildTimeTrend' % (
                        params['job'],
                        s2h_since_start,
                        server['url'])
        status = 'CRITICAL'
    elif (now_since_start >= convert_to_timedelta(params['warning'])):
        msg = '%s has been running for %s -  see %sconsole#footer' % (
                        params['job'],
                        s2h_since_start,
                        server['url'])
        status = 'WARNING'
    else:
        msg = '%s last successful run was %s ago' % (
                        params['job'],
                        s2h_since_start)
        status = 'OK'



    return(status, msg)




def controller():
    """Parse user input, fail quick if not enough parameters"""

    description = "A Nagios check for Jenkins."

    usage = """usage: %prog [options] -H SERVER -j JOB -w WARNING -c CRITICAL

    Make sure the last job is successful
             OR the current is not stuck (LastBuild)
    Warning and Critical are defined in minutes

    Ex :

     check_jenkins.py -H ci.jenkins-ci.org -j infa_release.rss -w 10 -c 42
    will check if the the job infa_release.rss is successful (or not stuck)

    """

    version = "%prog " + __version__
    parser = OptionParser(description=description, usage=usage,
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
    connection.add_option('-S', '--ssl', action="store_true", default=False,
                        help='If the connection requires ssl')
    parser.add_option_group(connection)

    extra = OptionGroup(parser, "Extra Options")
    extra.add_option('-v', action='store_true', dest='verbose', default=False,
                        help='Verbose mode')
    parser.add_option_group(extra)


    options, arguments = parser.parse_args()

    if (options.hostname == None):
        print "\n-H HOSTNAME"
        print "\nWe need the jenkins server hostname to connect to. --help for help"
        raise SystemExit, 2

    if (options.job == None):
        print "\n-j JOB"
        print "\nWe need the name of the job to check its health"
        raise SystemExit, 2

    if (options.warning == None):
        print "\n-w "
        print "\nHow long since the last successful build for a warning ?"
        print "ex: 3h or 180m or 10800s - default unit is minutes "
        raise SystemExit, 2

    if (options.critical == None):
        print "\n-c "
        print "\nHow long since the last successful build for a critical ?"
        print "ex: 4h or 240m or 14400s - default unit is minutes "
        raise SystemExit, 2

    return vars(options)


def main():
    """Runs all the functions"""

    # Command Line Parameters
    clp = controller()



    if clp['verbose']:
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
    if clp['ssl']:
        protocol = "https"
        # Unspecified port will be 80 by default, not correct if ssl is ON
        if (clp['port'] == 80):
            clp['port'] = 443
    else:
        protocol = "http"

    # Let's make sure we have a valid url
    if (clp['prefix'] != '/'):
        clp['prefix'] = '/%s/' %  clp['prefix']

    clp['url'] = "%s://%s:%s%sjob/%s/lastSuccessfulBuild/api/python" % (protocol,
                        clp['hostname'],
                        clp['port'],
                        clp['prefix'],
                        quote(clp['job']))

    clp['now'] = time()

    verboseprint("CLI Arguments : ", clp)


    out = eval(get_data(clp['url'], clp['username'], clp['password'],
            clp['timeout']))

    verboseprint("Reply from server :", out)


    status, message =  check_result(clp, out)

    print '%s - %s' % (status, message)
    # Exit statuses recognized by Nagios
    if   status == 'OK':
        raise SystemExit, 0
    elif status == 'WARNING':
        raise SystemExit, 1
    elif status == 'CRITICAL':
        raise SystemExit, 2
    elif status == 'UNKNOWN':
        raise SystemExit, 3
    else:
        raise SystemExit, 3


if __name__ == '__main__':
    main()

