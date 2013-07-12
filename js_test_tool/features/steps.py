"""
Steps for the Lettuce BDD specs.
"""

from lettuce import step, world


TEST_SUITE_DESC_PATH = 'jasmine/test_suite.yaml'
PASSING_SUITE_DESC_PATH = 'passing/test_suite.yaml'
FAILING_SUITE_DESC_PATH = 'failing/test_suite.yaml'

ACTUAL_COVERAGE_XML = 'js_coverage.xml'
ACTUAL_COVERAGE_HTML = 'js_coverage.html'
EXPECTED_COVERAGE_XML = 'expected/expected_js_coverage.xml'
EXPECTED_COVERAGE_HTML = 'expected/expected_js_coverage.html'
EXPECTED_TEST_REPORT = 'expected/expected_test_report.txt'


@step(u'When I run js-test-tool without coverage')
def run_tool_with_no_coverage(step):
    world.run_tool_with_args([TEST_SUITE_DESC_PATH])


@step(u'When I run js-test-tool with XML coverage')
def run_tool_with_xml_coverage(step):
    args = [TEST_SUITE_DESC_PATH, '--coverage-xml', ACTUAL_COVERAGE_XML]
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with HTML coverage')
def run_tool_with_html_coverage(step):
    args = [TEST_SUITE_DESC_PATH, '--coverage-html', ACTUAL_COVERAGE_HTML]
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with XML and HTML coverage')
def run_tool_with_html_coverage(step):
    args = [TEST_SUITE_DESC_PATH,
            '--coverage-html', ACTUAL_COVERAGE_HTML,
            '--coverage-xml', ACTUAL_COVERAGE_XML]
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with a passing test suite')
def run_tool_with_passing_test_suite(step):
    world.run_tool_with_args([PASSING_SUITE_DESC_PATH])


@step(u'When I run js-test-tool with a failing test suite')
def run_tool_with_failing_test_suite(step):
    world.run_tool_with_args([FAILING_SUITE_DESC_PATH])


@step(u'Then An XML coverage report is generated')
def check_xml_coverage_report(step):
    world.compare_files_at_paths(ACTUAL_COVERAGE_XML, EXPECTED_COVERAGE_XML)


@step(u'Then An HTML coverage report is generated')
def check_html_coverage_report(step):
    world.compare_files_at_paths(ACTUAL_COVERAGE_HTML, EXPECTED_COVERAGE_HTML)


@step(u'Then No coverage reports are generated')
def check_no_coverage_report(step):
    world.assert_no_file(ACTUAL_COVERAGE_XML)
    world.assert_no_file(ACTUAL_COVERAGE_HTML)


@step(u'Then I see the test suite results')
def check_test_suite_results(step):
    world.assert_tool_stdout(EXPECTED_TEST_REPORT)


@step(u'Given Coverage dependencies are configured')
def configure_coverage_dependencies(step):
    world.set_jscover(True)


@step(u'Given Coverage dependencies are missing')
def disable_coverage_dependencies(step):
    world.set_jscover(False)


@step(u'Then The tool exits with status "([^"]*)"')
def exits_with_status(step, status_code):
    world.assert_exit_code(status_code)