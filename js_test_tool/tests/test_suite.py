import unittest
import mock
import os
import os.path
from StringIO import StringIO
import yaml
import copy
from textwrap import dedent
from lxml import etree

from js_test_tool.tests.helpers import TempWorkspaceTestCase

from js_test_tool.suite import SuiteDescription, SuiteDescriptionError, \
    SuiteRenderer, SuiteRendererError


class SuiteDescriptionTest(TempWorkspaceTestCase):

    # Temporary directory paths to be created within our root temp dir
    TEMP_DIRS = ['src/subdir', 'spec/subdir', 'lib/subdir',
                 'src/empty', 'spec/empty', 'lib/empty',
                 'other_src', 'other_spec', 'other_lib',
                 'fixtures', 'single_file']

    # Test files to create.  Paths specified relative to the root temp dir.
    LIB_FILES = ['lib/1.js', 'lib/2.js', 'lib/subdir/3.js',
                 'other_lib/test.js',
                 'single_file/lib.js']

    SRC_FILES = ['src/1.js', 'src/2.js', 'src/subdir/3.js',
                 'other_src/test.js',
                 'single_file/src.js']

    SPEC_FILES = ['spec/1.js', 'spec/2.js', 'spec/subdir/3.js',
                  'other_spec/test.js',
                  'single_file/spec.js']

    FIXTURE_FILES = ['fixtures/fix1.html', 'fixtures/fix2.html',
                     'single_file/fix.html']

    IGNORE_FILES = ['src/ignore.txt', 'spec/ignore.txt', 'lib/ignore.txt']

    # Valid data used to create the YAML file describing the test suite
    YAML_DATA = {'test_suite_name': 'test_suite',
                 'lib_paths': ['lib', 'other_lib', 'single_file/lib.js'],
                 'src_paths': ['src', 'other_src', 'single_file/src.js'],
                 'spec_paths': ['spec', 'other_spec', 'single_file/spec.js'],
                 'fixture_paths': ['fixtures', 'single_file/fix.html'],
                 'test_runner': 'jasmine'}

    def setUp(self):
        """
        Generate fake JS files in a temporary directory.
        """

        # Call the superclass implementation to create the temp workspace
        super(SuiteDescriptionTest, self).setUp()

        # Create subdirectories for dependency, source, and spec files
        # Because we are using `makedirs()`, the intermediate directories
        # will also be created.
        for dir_path in self.TEMP_DIRS:
            os.makedirs(os.path.join(self.temp_dir, dir_path))

        # Create the test files
        all_files = (self.LIB_FILES + self.SRC_FILES
                     + self.SPEC_FILES + self.FIXTURE_FILES
                     + self.IGNORE_FILES)

        for file_path in all_files:
            full_path = os.path.join(self.temp_dir, file_path)
            with open(full_path, "w") as file_handle:
                file_handle.write(u'\u023Eest \u0256ata'.encode('utf8'))

    def test_valid_description(self):

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(self.YAML_DATA)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that the root directory is stored
        self.assertEqual(desc.root_dir(), self.temp_dir)

        # Check that we find the files we expect
        self.assertEqual(desc.suite_name(), self.YAML_DATA['test_suite_name'])
        self.assertEqual(desc.lib_paths(), self.LIB_FILES)
        self.assertEqual(desc.src_paths(), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES)
        self.assertEqual(desc.fixture_paths(), self.FIXTURE_FILES)
        self.assertEqual(desc.test_runner(), self.YAML_DATA['test_runner'])
        self.assertEqual(desc.prepend_path(), '')

    def test_different_working_dir(self):
        
        # Change the working directory temporarily
        # (the superclass will reset it afterwards)
        os.chdir(self.TEMP_DIRS[0])

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(self.YAML_DATA)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we find the files we expect
        self.assertEqual(desc.lib_paths(), self.LIB_FILES)
        self.assertEqual(desc.src_paths(), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES)
        self.assertEqual(desc.fixture_paths(), self.FIXTURE_FILES)
        self.assertEqual(desc.test_runner(), self.YAML_DATA['test_runner'])

    def test_double_dot_paths(self):

        # Transform the paths into relative paths
        rel_path_map = lambda path: os.path.join('..', path)
        yaml_data = copy.deepcopy(self.YAML_DATA)
        for key in ['lib_paths', 'src_paths', 'spec_paths', 'fixture_paths']:
            yaml_data[key] = map(rel_path_map, yaml_data[key])

        # Create a new root directory for the suite
        # temp_dir/suite_root
        # where the files are still in ../lib, ../src, etc.
        suite_root = os.path.join(self.temp_dir, 'suite_root')
        os.mkdir(suite_root)

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Expect an error for using relative paths,
        # even though the files exist
        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, suite_root)

    def test_no_such_root_dir(self):

        # Try to create a description with a non-existent root directory
        yaml_file = self._yaml_buffer(self.YAML_DATA)
        no_such_dir = os.path.join(self.temp_dir, 'no_such_dir')

        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, no_such_dir)

    def test_root_dir_is_file(self):

        # Try to create a description with a file (not directory) root
        yaml_file = self._yaml_buffer(self.YAML_DATA)
        file_path = os.path.join(self.temp_dir, self.SRC_FILES[0])

        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, file_path)

    def test_non_list_data(self):

        # Replace all list values with single values
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['lib_paths'] = 'lib'
        yaml_data['src_paths'] = 'src'
        yaml_data['spec_paths'] = 'spec'
        yaml_data['fixture_paths'] = 'fixtures'

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we get the right paths
        # (exclude files from the directories we left out)
        self.assertEqual(desc.lib_paths(), self.LIB_FILES[0:3])
        self.assertEqual(desc.src_paths(), self.SRC_FILES[0:3])
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES[0:3])

    def test_prepend_path_is_not_string(self):

        # Set prepend_path to non-string values
        for prepend_path in [42, ['list', 'of', 'items'], {'dict': 12}]:
            yaml_data = copy.deepcopy(self.YAML_DATA)
            yaml_data['prepend_path'] = prepend_path
            self._assert_invalid_desc(yaml_data)

    def test_yaml_is_list_not_dict(self):

        # Set up the YAML file to be a list of dicts instead
        # of a dict.
        # (This is easy to do by mistake in the YAML syntax).
        bad_data = [{key: value} for key, value in self.YAML_DATA.iteritems()]
        yaml_file = self._yaml_buffer(bad_data)

        # Expect an exception
        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, self.temp_dir)

    def test_no_lib_specified(self):

        # 'lib_paths' is an optional key
        yaml_data = copy.deepcopy(self.YAML_DATA)
        del yaml_data['lib_paths']

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we get an empty list of lib paths
        self.assertEqual(desc.lib_paths(), [])

    def test_no_fixtures_specified(self):

        # 'fixture_paths' is an optional key
        yaml_data = copy.deepcopy(self.YAML_DATA)
        del yaml_data['fixture_paths']

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we get an empty list of lib paths
        self.assertEqual(desc.fixture_paths(), [])

    def test_non_js_paths(self):

        # Add extra non-JS files
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['src_paths'].append('src.txt')
        yaml_data['spec_paths'].append('src.txt')
        yaml_data['lib_paths'].append('src.txt')

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we ignore those files
        self.assertEqual(desc.lib_paths(), self.LIB_FILES)
        self.assertEqual(desc.src_paths(), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES)

    def test_repeated_paths(self):

        # Repeat paths that are already included in the directories
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['src_paths'].append(self.SRC_FILES[0])
        yaml_data['spec_paths'].append(self.SPEC_FILES[0])
        yaml_data['lib_paths'].append(self.LIB_FILES[0])
        yaml_data['fixture_paths'].append(self.FIXTURE_FILES[0])

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that we ignore repeats
        self.assertEqual(desc.lib_paths(), self.LIB_FILES)
        self.assertEqual(desc.src_paths(), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(), self.SPEC_FILES)
        self.assertEqual(desc.fixture_paths(), self.FIXTURE_FILES)

    def test_prepend_path(self):

        # Add a path to prepend to source paths in reports
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['prepend_path'] = 'base/path'

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that the prepend path is stored
        self.assertEqual(desc.prepend_path(), 'base/path')

    def test_exclude_from_page(self):

        # Add in a rule to exclude files in other_* dir
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['exclude_from_page'] = 'other_[^/]*/.*'

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that the root directory is stored
        self.assertEqual(desc.root_dir(), self.temp_dir)

        # Check that we find the files we expect
        expected_lib = self.LIB_FILES[:]
        expected_lib.remove('other_lib/test.js')

        expected_src = self.SRC_FILES[:]
        expected_src.remove('other_src/test.js')

        expected_spec = self.SPEC_FILES[:]
        expected_spec.remove('other_spec/test.js')

        self.assertEqual(desc.lib_paths(only_in_page=True), expected_lib)
        self.assertEqual(desc.src_paths(only_in_page=True), expected_src)
        self.assertEqual(desc.spec_paths(only_in_page=True), expected_spec)

    def test_include_and_exclude_from_page(self):

        # Add in a rule to exclude files in other_* dir
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['exclude_from_page'] = 'other_[^/]*/.*'

        # Add an override rule to always include other_*/test.js
        yaml_data['include_in_page'] = 'other_[^/]*/test.js'

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Create the suite description using the YAML file
        desc = SuiteDescription(yaml_file, self.temp_dir)

        # Check that the root directory is stored
        self.assertEqual(desc.root_dir(), self.temp_dir)

        # Check that we still get all the files back
        # (the include rule overrides the exclude rule)
        self.assertEqual(desc.lib_paths(only_in_page=True), self.LIB_FILES)
        self.assertEqual(desc.src_paths(only_in_page=True), self.SRC_FILES)
        self.assertEqual(desc.spec_paths(only_in_page=True), self.SPEC_FILES)

    def test_missing_required_data(self):

        for key in ['test_suite_name', 'src_paths', 'spec_paths', 'test_runner']:

            # Delete the required key from the description
            yaml_data = copy.deepcopy(self.YAML_DATA)
            del yaml_data[key]

            # Print a message to make failures more informative
            print "Missing key '{}' should raise an exception".format(key)

            # Check that we get an exception
            self._assert_invalid_desc(yaml_data)

    def test_empty_required_list(self):

        for key in ['src_paths', 'spec_paths']:

            # Replace the key with an empty list
            yaml_data = copy.deepcopy(self.YAML_DATA)
            yaml_data[key] = []

            # Print a message to make failures more informative
            print "Empty list for '{}' should raise an exception".format(key)

            # Check that we get an exception
            self._assert_invalid_desc(yaml_data)

    def test_invalid_test_runner(self):
        yaml_data = copy.deepcopy(self.YAML_DATA)
        yaml_data['test_runner'] = 'invalid_test_runner'

        # Check that we get an exception
        self._assert_invalid_desc(yaml_data)

    def test_invalid_suite_name(self):

        invalid_names = [
            'with a space',
            'with/slash',
            'with?question',
            'with+plus',
            'with&amp'
        ]

        # Suite names need to be URL-encodable
        for invalid in invalid_names:
            print invalid
            yaml_data = copy.deepcopy(self.YAML_DATA)
            yaml_data['test_suite_name'] = invalid
            self._assert_invalid_desc(yaml_data)

    def _assert_invalid_desc(self, yaml_data):
        """
        Given `yaml_data` (dict), assert that it raises
        a `SuiteDescriptionError`.
        """

        # Create an in-memory YAML file from the data
        yaml_file = self._yaml_buffer(yaml_data)

        # Expect an exception when we try to parse the YAML file
        with self.assertRaises(SuiteDescriptionError):
            SuiteDescription(yaml_file, self.temp_dir)

    @staticmethod
    def _yaml_buffer(data_dict):
        """
        Create an in-memory buffer with YAML-encoded data
        provided by `data_dict` (a dictionary).

        Returns the buffer (a file-like object).
        """

        # Encode the `data_dict` as YAML and write it to the buffer
        yaml_str = yaml.dump(data_dict)

        # Create a file-like string buffer to hold the YAML data
        string_buffer = StringIO(yaml_str)

        return string_buffer


class SuiteRendererTest(unittest.TestCase):

    JASMINE_TEST_RUNNER_SCRIPT = dedent("""
        (function() {
            var jasmineEnv = jasmine.getEnv();
            jasmineEnv.updateInterval = 1000;

            var reporter = new jasmine.JsonReporter("js_test_tool_results", "test-suite");
            jasmineEnv.addReporter(reporter);

            jasmineEnv.specFilter = function(spec) {
                return reporter.specFilter(spec);
            };

            var currentWindowOnload = window.onload;

            window.onload = function() {
                if (currentWindowOnload) {
                    currentWindowOnload();
                }

                execJasmine();
            };

            function execJasmine() {
                try {
                    jasmineEnv.execute();
                }
                catch(err) {
                    window.js_test_tool.reportError(err);
                }
            }

            if (!window.js_test_tool) {
                window.js_test_tool = {};
                window.js_test_tool.reportError = function(err) {
                    var resultDiv = document.getElementById("js_test_tool_results");
                    var errDiv = document.getElementById("js_test_tool_error");

                    // If an error <div> is defined (e.g. not in dev mode)
                    // then write the error to that <div>
                    // so the Browser can report it
                    if (errDiv) {
                        errDiv.innerHTML = err.toString()
                        if ('stack' in err) {
                            errDiv.innerHTML += "\\n" + err.stack
                        }

                        // Signal to the browser that we're done
                        // to avoid blocking until timeout
                        resultsDiv.className = "done";
                    }

                    // Re-throw the error (e.g. for dev mode)
                    else {
                        throw err;
                    }
                }
            }

        })();
    """).strip()

    JASMINE_LOAD_FIXTURES_SCRIPT = dedent("""
        // Load fixtures if using jasmine-jquery
        if (jasmine.getFixtures) {
            jasmine.getFixtures().fixturesPath = "/suite/test-suite/include/";
        }
    """).strip()

    ALERT_STUB_SCRIPT = dedent("""
        // Stub out modal dialog alerts, which will prevent
        // us from accessing the test results in the DOM
        window.confirm = function(){return true;};
        window.alert = function(){return;};
    """).strip()

    def setUp(self):

        # Create the renderer we will use
        self.renderer = SuiteRenderer()

    def test_unicode(self):

        # Create a mock test suite description
        desc = self._mock_desc(['lib1.js', 'lib2.js'],
                               ['src1.js', 'src2.js'],
                               ['spec1.js', 'spec2.js'],
                               'jasmine')

        # Render the description as HTML
        html = self.renderer.render_to_string('test-suite', desc)

        # Expect that we get a `unicode` string
        self.assertTrue(isinstance(html, unicode))

    def test_jasmine_runner_includes(self):

        jasmine_libs = ['jasmine/jasmine.js',
                        'jasmine/jasmine-json.js']
        lib_paths = ['lib1.js', 'lib2.js']
        src_paths = ['src1.js', 'src2.js']
        spec_paths = ['spec1.js', 'spec2.js']

        # Create a mock test suite description
        desc = self._mock_desc(lib_paths, src_paths, spec_paths, 'jasmine')

        # Check that we get the right script includes
        suite_includes = lib_paths + src_paths + spec_paths
        self._assert_js_includes(jasmine_libs, suite_includes, desc)

        # Check that only "include_in_page" scripts were used
        desc.lib_paths.assert_called_with(only_in_page=True)
        desc.src_paths.assert_called_with(only_in_page=True)
        desc.spec_paths.assert_called_with(only_in_page=True)

    def test_no_lib_files(self):

        jasmine_libs = ['jasmine/jasmine.js',
                        'jasmine/jasmine-json.js']
        src_paths = ['src.js']
        spec_paths = ['spec.js']

        # Create a mock test suite description
        desc = self._mock_desc([], src_paths, spec_paths, 'jasmine')

        # Check that we get the right script includes
        suite_includes = src_paths + spec_paths
        self._assert_js_includes(jasmine_libs, suite_includes, desc)

    def test_render_jasmine_runner(self):

        # Create a test runner page
        tree = self._test_runner_html()

        # Expect that a <div> exists with the correct ID for the results
        div_id = SuiteRenderer.RESULTS_DIV_ID
        elems = tree.xpath('//div[@id="{}"]'.format(div_id))
        self.assertEqual(len(elems), 1)

        # Expect that a <div> exists for reporting JS errors
        div_id = SuiteRenderer.ERROR_DIV_ID
        elems = tree.xpath('//div[@id="{}"]'.format(div_id))
        self.assertEqual(len(elems), 1)

        # Expect that the right scripts are available
        self._assert_script(tree, self.JASMINE_TEST_RUNNER_SCRIPT, -1)
        self._assert_script(tree, self.JASMINE_LOAD_FIXTURES_SCRIPT, -2)

    def test_render_jasmine_dev_mode(self):

        # Create a test runner page in dev mode
        tree = self._test_runner_html(dev_mode=True)

        # Should get the same script, except with an HTML reporter
        # instead of the custom JSON reporter
        expected_script = self.JASMINE_TEST_RUNNER_SCRIPT.replace(
            'JsonReporter("js_test_tool_results", "test-suite")',
            'HtmlReporter()')

        # Check that we have the right script available
        self._assert_script(tree, expected_script, -1)

    def test_jasmine_dev_mode_includes(self):

        # Configure the renderer to use dev mode
        self.renderer = SuiteRenderer(dev_mode=True)

        # Include the HTMLReporter instead of the JSON reporter
        jasmine_libs = ['jasmine/jasmine.js',
                        'jasmine/jasmine-html.js']
        lib_paths = ['lib1.js', 'lib2.js']
        src_paths = ['src1.js', 'src2.js']
        spec_paths = ['spec1.js', 'spec2.js']

        # Create a mock test suite description
        desc = self._mock_desc(lib_paths, src_paths, spec_paths, 'jasmine')

        # Check that we get the right script includes
        suite_includes = lib_paths + src_paths + spec_paths
        self._assert_js_includes(jasmine_libs, suite_includes, desc)

    def test_stub_alerts(self):

        tree = self._test_runner_html()
        self._assert_script(tree, self.ALERT_STUB_SCRIPT, 0)

    def test_stub_alerts_dev_mode(self):

        tree = self._test_runner_html(dev_mode=True)
        self._assert_script(tree, self.ALERT_STUB_SCRIPT, 0)

    def test_undefined_template(self):

        # Create a mock test suite description with an invalid test runner
        desc = self._mock_desc([], [], [], 'invalid_test_runner')

        # Should get an exception that the template could not be found
        with self.assertRaises(SuiteRendererError):
            self.renderer.render_to_string('test-suite', desc)

    def test_template_render_error(self):

        # Create a mock test suite description with no includes
        desc = self._mock_desc([], [], [], 'jasmine')

        # Patch Jinja2's `render()` function
        with mock.patch.object(SuiteRenderer, 'render_template') as render_func:

            # Have the render function raise an exception
            render_func.side_effect = ValueError()

            # Expect that we get a `SuiteRendererError`
            with self.assertRaises(SuiteRendererError):
                self.renderer.render_to_string('test-suite', desc)

    def _test_runner_html(self, dev_mode=False):
        """
        Return a parsed tree of the test runner page HTML.
        """
        # Configure the renderer to use dev mode
        self.renderer = SuiteRenderer(dev_mode=dev_mode)

        # Create a mock test suite description
        desc = self._mock_desc([], [], [], 'jasmine')

        # Render the description to HTML, enabling dev mode
        html = self.renderer.render_to_string('test-suite', desc)

        # Parse the HTML
        return etree.HTML(html)

    def _assert_script(self, html_tree, expected_script, script_index):
        """
        Assert that the parsed HTML tree `html_tree` contains
        `expected_script` in a <script> tag at `script_index` (starting at 0).
        """
        # Retrieve the script elements
        script_elems = html_tree.xpath('/html/head/script')

        # Expect there are enough elements to retrieve the index
        self.assertTrue(len(script_elems) > abs(script_index))

        # Retrieve the script element
        actual_script = script_elems[script_index].text.strip()

        # Expect that we got the right script
        self.assertEqual(actual_script, expected_script)

    def _assert_js_includes(self, runner_includes, suite_includes, suite_desc):
        """
        Render `suite_desc` (a `SuiteDescription` instance or mock) to
        `html`, then asserts that the `html` contains `<script>` tags with
        `runner_includes` (files included by default, with a `/runner/` prefix)
        and `suite_includes` (files included by the test suite,
        with a `/suite/include` prefix)
        """
        # Render the description as HTML
        html = self.renderer.render_to_string('test-suite', suite_desc)

        # Parse the HTML
        tree = etree.HTML(html)

        # Retrieve all <script> inclusions
        script_elems = tree.xpath('/html/head/script')

        # Prepend the runner and suite includes
        runner_includes = [os.path.join('/runner', path)
                           for path in runner_includes]
        suite_includes = [os.path.join('/suite', 'test-suite', 'include', path)
                          for path in suite_includes]

        # Check that they match the sources we provided, in order
        all_paths = [element.get('src') for element in script_elems
                     if element.get('src') is not None]

        self.assertEqual(all_paths, runner_includes + suite_includes)

    @staticmethod
    def _mock_desc(lib_paths, src_paths, spec_paths, test_runner):
        """
        Create a mock SuiteDescription configured to return
        `lib_paths` (paths to JS dependency files)
        `src_paths` (paths to JS source files)
        `spec_paths` (paths to JS spec files)
        `test_runner` (name of the test runner, e.g. Jasmine)

        Returns the configured mock
        """
        desc = mock.MagicMock(SuiteDescription)

        desc.lib_paths.return_value = lib_paths
        desc.src_paths.return_value = src_paths
        desc.spec_paths.return_value = spec_paths
        desc.test_runner.return_value = test_runner

        return desc
