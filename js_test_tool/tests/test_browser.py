from unittest import TestCase
import json
from js_test_tool.browser import Browser, BrowserError
from js_test_tool.suite import SuiteRenderer
from js_test_tool.tests.helpers import StubServer


class BrowserTest(TestCase):

    def setUp(self):

        # Create a stub server on a local port
        self.stub_server = StubServer()

        # Create the browser (use PhantomJS)
        self.browser = Browser('phantomjs')

    def tearDown(self):

        # Stop the server and free the port
        self.stub_server.stop()

        # Stop the browser
        self.browser.quit()

    def test_get_page_results(self):

        # Configure the stub server to send a valid test results page
        results = [{'testGroup': 'Adder tests',
                    'testName': 'it should start at zero',
                    'testStatus': 'pass',
                    'testDetail': ''},
                   {'testGroup': 'Adder tests',
                    'testName': 'it should add to the sum',
                    'testStatus': 'fail',
                    'testDetail': 'Stack trace'},
                   {'testGroup': 'Multiplier test',
                    'testName': 'it should multiply',
                    'testStatus': 'pass',
                    'testDetail': ''}]

        content = u'<div id="{}">{}</div>'.format(SuiteRenderer.RESULTS_DIV_ID,
                                                  json.dumps(results))
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Check the results
        # Keys should be munged into Python-style var names
        expected_results = [{'test_group': 'Adder tests',
                             'test_name': 'it should start at zero',
                             'status': 'pass',
                             'detail': ''},
                            {'test_group': 'Adder tests',
                             'test_name': 'it should add to the sum',
                             'status': 'fail',
                             'detail': 'Stack trace'},
                            {'test_group': 'Multiplier test',
                             'test_name': 'it should multiply',
                             'status': 'pass',
                             'detail': ''}]

        self.assertEqual(expected_results, output_results)

    def test_get_page_results_control_chars(self):

        # Try sending a control char
        json_data = ('[{"testGroup":"when song has been paused",' +
                     '"testName":"should indicate that the song is currently paused",' +
                     '"testStatus":"fail",' +
                     '"testDetail":"Error: Expected true to be falsy.\n at new jasmine.ExpectationResult"}]')

        content = u'<div id="{}">{}</div>'.format(SuiteRenderer.RESULTS_DIV_ID,
                                                  json_data)
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect that we get the results back
        expected_results = [
            {u'test_group': u"when song has been paused",
             u'test_name': u"should indicate that the song is currently paused",
             u'status': u"fail",
             u'detail': u"Error: Expected true to be falsy.\n at new jasmine.ExpectationResult"}]

        self.assertEqual(expected_results, output_results)

    def test_no_results(self):
        # Configure the stub server to send an empty <div>
        content = u'<div id="{}">[]</div>'.format(SuiteRenderer.RESULTS_DIV_ID)
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect we get an empty list back
        self.assertEqual(output_results, [])

    def test_error_conditions(self):

        div_id = SuiteRenderer.RESULTS_DIV_ID
        error_responses = [(200, u'<div id="wrong_id"></div>'),
                           (200, u''),
                           (200, u'<div id="{}">Not JSON</div>'.format(div_id)),
                           (200, u'<div id="{}">[{"missing_keys":"val"}]</div>'),
                           (404, u'Not found'),
                           (500, u'Error occurred')]

        server_url = self.stub_server.root_url()

        for (status_code, content) in error_responses:

            # Configure the stub server to send an invalid response
            self.stub_server.set_response(status_code, content)

            # Expect an exception
            with self.assertRaises(BrowserError):
                self.browser.get_page_results(server_url)

    def test_no_response(self):

        # Configure the server to ignore requests
        self.stub_server.set_ignore_requests(True)

        server_url = self.stub_server.root_url()

        # Configure the Browser to timeout quickly
        old_timeout = Browser.TIMEOUT

        def cleanup():
            Browser.TIMEOUT = old_timeout
        self.addCleanup(cleanup)

        Browser.TIMEOUT = 0.2

        # Expect the Browser to give an error when it times out
        with self.assertRaises(BrowserError):
            self.browser.get_page_results(server_url)