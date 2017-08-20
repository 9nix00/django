import sys
import unittest
from io import StringIO

from django.db import connection
from django.test import TestCase
from django.test.runner import DiscoverRunner

from .models import Person


@unittest.skipUnless(connection.vendor == 'sqlite', 'Only run on sqlite so we can check output SQL.')
class TestDebugSQL(unittest.TestCase):

    class PassingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='pass').count()

    class FailingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='fail').count()
            self.fail()

    class ErrorTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='error').count()
            raise Exception

    class PassingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-pass').count()

    class FailingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-fail').count()
                self.fail()

    class ErrorSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-error').count()
                raise Exception

    def _test_output(self, verbosity):
        runner = DiscoverRunner(debug_sql=True, verbosity=0)
        suite = runner.test_suite()
        suite.addTest(self.FailingTest())
        suite.addTest(self.ErrorTest())
        suite.addTest(self.PassingTest())
        suite.addTest(self.PassingSubTest())
        suite.addTest(self.FailingSubTest())
        suite.addTest(self.ErrorSubTest())
        old_config = runner.setup_databases()
        stream = StringIO()
        resultclass = runner.get_resultclass()
        runner.test_runner(
            verbosity=verbosity,
            stream=stream,
            resultclass=resultclass,
        ).run(suite)
        runner.teardown_databases(old_config)

        return stream.getvalue()

    def test_output_normal(self):
        full_output = self._test_output(1)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)
        for output in self.verbose_expected_outputs:
            self.assertNotIn(output, full_output)

    def test_output_verbose(self):
        full_output = self._test_output(2)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)
        for output in self.verbose_expected_outputs:
            self.assertIn(output, full_output)

    expected_outputs = [
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'error';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'fail';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-error';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-fail';'''),
    ]

    verbose_expected_outputs = [
        # Output format changed in Python 3.5+
        x.format('' if sys.version_info < (3, 5) else 'TestDebugSQL.') for x in [
            'runTest (test_runner.test_debug_sql.{}FailingTest) ... FAIL',
            'runTest (test_runner.test_debug_sql.{}ErrorTest) ... ERROR',
            'runTest (test_runner.test_debug_sql.{}PassingTest) ... ok',
            'runTest (test_runner.test_debug_sql.{}PassingSubTest) ... ok',
            # If there are errors/failures in subtests but not in test itself,
            # the status is not written. That behavior comes from Python.
            'runTest (test_runner.test_debug_sql.{}FailingSubTest) ...',
            'runTest (test_runner.test_debug_sql.{}ErrorSubTest) ...',
        ]
    ] + [
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'pass';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-pass';'''),
    ]
