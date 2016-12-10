#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

https://launchpad.net/python-jenkins
https://wiki.jenkins-ci.org/display/JENKINS/Remote+access+API
http://nagiosplug.sourceforge.net/developer-guidelines.html


Few doctests to run :

 $ python -m doctest check_jenkins.py -v

"""
__author__ = 'Julien Rottenberg'
__date__ = "December 2011"
__url__ = "https://github.com/jrottenberg/check_jenkins"

__version__ = "1.0"
__credits__ = """https://launchpad.net/python-jenkins - this code is a trimmed
down version with nagios specific code"""

from optparse import OptionParser, OptionGroup
from datetime import timedelta, datetime
from time import strftime, gmtime
import base64
import urllib2
from urllib2 import HTTPError, URLError
from urllib import quote
from socket import setdefaulttimeout

class CheckJenkins(object):

    def get_data(self, url, username, password, timeout):
        """
        Initialize the connection to Jenkins
        """

        request = urllib2.Request(url)
        request.add_header('User-Agent',
                'check_jenkins/%s %s' % (__version__, __url__))
        if (username and password):
            base64string = base64.b64encode('%s:%s' % (username, password))
            request.add_header("Authorization", "Basic %s" % base64string)

        try:
            setdefaulttimeout(timeout)
            return urllib2.urlopen(request).read()
        except HTTPError:
            print 'CRITICAL: Error on %s does the job exist or ever ran ?' % url
            raise SystemExit, 2
        except URLError:
            print 'CRITICAL: Error on %s Double check the server name' % url
            raise SystemExit, 2


    def seconds2human(self, my_time):
        """
        Convert given seconds into human readable string
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


    def check_result(self, params, server):
        """
        From the server response and input parameter
        check if the job status should trigger an alert

        Jenkins results
        http://javadoc.jenkins-ci.org/hudson/model/Result.html
        """
        if server['building']:
            # I assume Server and client are on the same TimeZone
            # the API doesn't tell me where is the server (only /systemInfo)
            job_started = datetime.fromtimestamp(int(server['timestamp']) / 1000)
            time_delta = (params['now'] - job_started)

            # New in version 2.7 --> datetime.timedelta.total_seconds
            # we want python >= 2.4 so we will do it ourselves
            seconds_since_start = time_delta.seconds + time_delta.days * 86400
            job_duration = self.seconds2human(seconds_since_start)
            if (seconds_since_start >= params['critical'] * 60):
                msg = '%s has been running for %s, see %sconsole#footer' % (
                                params['job'],
                                job_duration,
                                server['url'])
                status = 'CRITICAL'
            elif (seconds_since_start >= params['warning'] * 60):
                msg = '%s has been running for %s, see %sconsole#footer' % (
                                params['job'],
                                job_duration,
                                server['url'])
                status = 'WARNING'
            else:
                msg = '%s still running after %s, watch it on %sconsole#footer' % (
                                params['job'],
                                job_duration,
                                server['url'])
                status = 'OK'
        else:
            # Easy part, the job has completed ...
            if server['result'] == 'SUCCESS':
                duration = self.seconds2human(server['duration'] / 1000)
                msg = '%s exited normally after %s' % (params['job'], duration)
                status = 'OK'

            elif server['result'] == 'UNSTABLE':
                duration = self.seconds2human(server['duration'] / 1000)
                msg = '%s is marked as unstable after %s, see %sconsole#footer' % (
                    params['job'], duration, server['url'])
                status = 'WARNING'

            elif server['result'] == 'FAILURE':
                msg = '%s exited with an error, see %sconsole#footer' % (
                    params['job'], server['url'])
                status = 'CRITICAL'

            elif server['result'] == 'ABORTED':
                msg = '%s has been aborted, see %sconsole#footer' % (
                        params['job'], server['url'])
                status = 'UNKNOWN'
            else:
                # If you get there, patch welcome
                msg = '%s is in a not known state, Jenkins API issue ? see %s' % (
                        params['job'], server['url'])
                status = 'UNKNOWN'

        return(status, msg)


    def usage(self):
        """
        Return usage text so it can be used on failed human interactions
        """

        usage_string = """
        usage: %prog [options] -H SERVER -j JOB -w WARNING -c CRITICAL

        Make sure the last job is successful
                 OR the current is not stuck (LastBuild)
        Warning and Critical are defined in minutes

        Ex :

         check_jenkins.py -H ci.jenkins-ci.org -j infa_release.rss -w 10 -c 42
        will check if the the job infa_release.rss is successful
        or not stuck for more than 10 (warn) 42 minutes (critical alert)

        """

        return usage_string


    def display(self, arguments):
        print
        """Non recognized option %s
    Please use --help for usage""" % arguments
        print
        self.usage()
        raise SystemExit, 2

    def controller(self):
        """
        Parse user input, fail quick if not enough parameters
        """

        description = "A Nagios plugin to check the status of a Jenkins job."

        version = "%prog " + __version__

        parser = OptionParser(description=description, usage=self.usage(),
                                version=version)

        parser.add_option('-H', '--hostname', type='string',
                            help='Jenkins hostname')

        parser.add_option('-j', '--job', type='string',
                            help='Job, use quotes if it contains space')

        parser.add_option('-w', '--warning', type='int',
                            help='Warning threshold in minutes')

        parser.add_option('-c', '--critical', type='int',
                            help='Critical threshold in minutes')

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

        if (arguments != []):
            self.display(arguments)
            """Non recognized option %s
        Please use --help for usage""" % arguments
            print self.usage()
            raise SystemExit, 2

        if (options.hostname == None):
            print "\n-H HOSTNAME"
            print "\nWe need the jenkins server hostname to connect to."
            print "Use  --help for help"
            print self.usage
            raise SystemExit, 2

        if (options.job == None):
            print "\n-j JOB"
            print "\nWe need the name of the job to check its health"
            print self.usage()
            raise SystemExit, 2

        if (options.warning == None):
            print "\n-w MINUTES"
            print "\nHow many minutes the job should run ?"
            print self.usage()
            raise SystemExit, 2

        if (options.critical == None):
            print "\n-c MINUTES"
            print "\nHow many minutes maximum the job should run ?"
            print self.usage()
            raise SystemExit, 2

        return vars(options)

       


if __name__ == '__main__':
    """
    Runs all the functions
    """
    jen = CheckJenkins()
    # Command Line Parameters
    user_in = jen.controller()

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

    # Let's make sure we have a valid url
    if (user_in['prefix'] != '/'):
        user_in['prefix'] = '/%s/' % user_in['prefix']

    user_in['url'] = "%s://%s:%s%sjob/%s/lastBuild/api/python" % (protocol,
                        user_in['hostname'],
                        user_in['port'],
                        user_in['prefix'],
                        quote(user_in['job']))

    # Get the current time, no need to get the microseconds
    user_in['now'] = datetime.now().replace(microsecond=0)

    verboseprint("CLI Arguments : ", user_in)

    jenkins_out = eval(jen.get_data(user_in['url'], user_in['username'],
        user_in['password'],
        user_in['timeout']))

    verboseprint("Reply from server :", jenkins_out)

    status, message = jen.check_result(user_in, jenkins_out)

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

