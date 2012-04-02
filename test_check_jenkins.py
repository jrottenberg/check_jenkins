#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from optparse import OptionParser, OptionGroup
from datetime import timedelta, datetime
from time import strftime, gmtime
import urllib2

from urllib2 import HTTPError, URLError
from urllib import quote
import base64
from check_jenkins import CheckJenkins
from StringIO import StringIO


class TestCheckJenkins(unittest.TestCase):
    test_suite_seconds2human = ((60, '00:01:00'), 
                                (300, '00:05:00'),
                                (3601, '01:00:01'),
                                (86401, '1 day, 00:00:01'),
                                (604800, '7 days, 00:00:00'))

    in_p = {'job': 'test', 'warning': 60, 'critical': 120, 'now': datetime(2012, 2, 5, 16, 12, 41, 999999)}
                                
                                
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.cj = CheckJenkins()



    class MyHTTPHandler(urllib2.HTTPHandler):
        def http_open(self, req):
            return self.mock_response(req)

        def mock_response(self, req):
            if req.get_full_url() == "http://localhost/test":
                resp = urllib2.addinfourl(StringIO("mock file"), "mock message", req.get_full_url())
                resp.code = 200
                resp.msg = "OK"
                return resp
            if req.get_full_url() == "http://localhost/typo":
                resp = urllib2.addinfourl(StringIO("mock file"), "mock message", req.get_full_url())
                resp.code = 404
                resp.msg = "Not Found"
                return resp    
            else:
                raise SystemExit, 2
            

    def test_get_data_ok(self):
        my_opener = urllib2.build_opener(self.MyHTTPHandler)
        urllib2.install_opener(my_opener)
        dl_ok = self.cj.get_data('http://localhost/test', 'user', 'pass', 1)


    def test_get_data_typo(self):
        my_opener = urllib2.build_opener(self.MyHTTPHandler)
        urllib2.install_opener(my_opener)
        try:
            dl_typo = self.cj.get_data('http://localhost/typo', 'user', 'pass', 1)
        except SystemExit, e: 
            self.assertRaises(HTTPError)

    def test_get_data_error(self):
        my_opener = urllib2.build_opener(self.MyHTTPHandler)
        urllib2.install_opener(my_opener)
        try:
            dl_error = self.cj.get_data('http://fdsfsd', 'user', 'pass', 1)
        except SystemExit, e: 
            self.assertRaises(URLError)



    def test_seconds2human(self):
        for integer, string in self.test_suite_seconds2human:                
            self.assertEqual(string, self.cj.seconds2human(integer))


    def test_check_result_ok(self):
        result_done = self.cj.check_result(self.in_p, {'building': False, 'result': 'SUCCESS', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('OK', 'test exited normally after 00:00:17'), result_done)
        
        result_building = self.cj.check_result(self.in_p, {'building': True, 'result': '', 'timestamp': '1328483562000', 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('OK', 'test still running after 00:59:59, watch it on http://localhost/job/test/6/console#footer'), result_building)       

    def test_check_result_critical(self):
        result_done = self.cj.check_result(self.in_p, {'building': False, 'result': 'FAILURE', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('CRITICAL', 'test exited with an error, see http://localhost/job/test/6/console#footer'), result_done)

        result_building = self.cj.check_result(self.in_p,  {'building': True, 'result': '', 'building': True, 'timestamp': '1328476362000', 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('CRITICAL', 'test has been running for 02:59:59, see http://localhost/job/test/6/console#footer'), result_building)
                                          

    def test_check_result_warning(self):
        result_done = self.cj.check_result(self.in_p,  {'building': False, 'result': 'UNSTABLE', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('WARNING', 'test is marked as unstable after 00:00:17, see http://localhost/job/test/6/console#footer'), result_done)
        
        result_building = self.cj.check_result(self.in_p,  {'building': True, 'result': '', 'timestamp': '1328479962000', 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('WARNING', 'test has been running for 01:59:59, see http://localhost/job/test/6/console#footer'), result_building)       
                
                
    def test_check_result_aborted(self):
        result = self.cj.check_result(self.in_p, {'building': False, 'result': 'ABORTED', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('UNKNOWN', 'test has been aborted, see http://localhost/job/test/6/console#footer'), result)
           
        result = self.cj.check_result(self.in_p, {'building': False, 'result': 'UNKNOWN', 'duration': 17852, 'url': 'http://localhost/job/test/6/'})
        self.assertEqual(('UNKNOWN', 'test is in a not known state, Jenkins API issue ? see http://localhost/job/test/6/'), result)
           
                                

    def test_controller(self):
        optionparser_mock = Mock()
        

        
        
if __name__ == '__main__':
    unittest.main()
