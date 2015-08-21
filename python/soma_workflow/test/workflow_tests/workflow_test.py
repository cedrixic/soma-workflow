from __future__ import with_statement
'''
@author: laure.hugo@cea.fr
@author: Soizic Laguitton
@organization: U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''

import unittest
import sys
import os
import shutil
import tempfile
import StringIO
import socket

from soma_workflow.client import WorkflowController
from soma_workflow.configuration import Configuration, LIGHT_MODE
from soma_workflow.test.utils import get_user_id
from soma_workflow.test.utils import suppress_stdout

from soma_workflow.test.workflow_tests import WorkflowExamplesLocal
from soma_workflow.test.workflow_tests import WorkflowExamplesShared
from soma_workflow.test.workflow_tests import WorkflowExamplesSharedTransfer
from soma_workflow.test.workflow_tests import WorkflowExamplesTransfer


class WorkflowTest(unittest.TestCase):

    LOCAL_PATH = "local path"
    FILE_TRANSFER = "file transfer"
    SHARED_RESOURCE_PATH = "shared resource path"
    SHARED_TRANSFER = "file transfer and shared resource path"

    wf_ctrl = None
    path_management = None
    wf_examples = None
    wf_id = None

    @classmethod
    def setup_wf_controller(cls, workflow_controller):
        cls.wf_ctrl = workflow_controller

    @classmethod
    def setup_path_management(cls, path_management):
        '''
        * path_management: LOCAL_PATH, FILE_TRANSFER or SHARED_RESOURCE_PATH
        '''
        cls.path_management = path_management

    def setUp(self):
        if self.path_management == self.LOCAL_PATH:
            workflow_examples = WorkflowExamplesLocal()
        elif self.path_management == self.FILE_TRANSFER:
            workflow_examples = WorkflowExamplesTransfer()
        elif self.path_management == self.SHARED_RESOURCE_PATH:
            workflow_examples = WorkflowExamplesShared()
        elif self.path_management == self.SHARED_TRANSFER:
            workflow_examples = WorkflowExamplesSharedTransfer()
        self.wf_examples = workflow_examples

    def tearDown(self):
        if self.wf_id:
            self.__class__.wf_ctrl.delete_workflow(self.wf_id)
        if os.path.isdir(self.wf_examples.output_dir):
            shutil.rmtree(self.wf_examples.output_dir)

    @classmethod
    def run_test(cls, debug=False, interactive=False):
        sys.stdout.write("********* soma-workflow tests: WORKFLOW *********\n")

        config_file_path = Configuration.search_config_path()
    #    sys.stdout.write("Configuration file: " + config_file_path + "\n")
        resource_ids = Configuration.get_configured_resources(config_file_path)

        for resource_id in resource_ids:
            sys.stdout.write("============ Resource : " + resource_id +
                             " =================== \n")
            config = Configuration.load_from_file(resource_id,
                                                  config_file_path)
            if not interactive and config.get_mode() != LIGHT_MODE:
                sys.stdout.write('Resource %s is not tested in '
                                 'non-interactive mode\n' % resource_id)
                continue  # skip login/password ask
            if interactive:
                sys.stdout.write("Do you want to test the resource "
                                 "%s (Y/n) ? " % resource_id)
                test_resource = sys.stdin.readline()
                if test_resource.strip() in ['no', 'n', 'N', 'No', 'NO']:
                    # Skip the resource
                    sys.stdout.write('Resource %s is not tested \n'
                                     % resource_id)
                    continue
            (login, password) = get_user_id(resource_id, config)

            # use a temporary sqlite database in soma-workflow to avoid
            # concurrent access problems
            tmpdb = tempfile.mkstemp('.db', prefix='swf_')
            os.close(tmpdb[0])
            os.unlink(tmpdb[1])
            config._database_file = tmpdb[1]

            try:

                with suppress_stdout(debug):
                    wf_controller = WorkflowController(resource_id,
                                                      login,
                                                      password,
                                                      config=config)
                    cls.setup_wf_controller(wf_controller)

                allowed_config = cls.allowed_config[:]
                for configuration in cls.allowed_config:
                    if config.get_mode() != configuration[0]:
                        allowed_config.remove(configuration)
                if len(allowed_config) == 0:
                    sys.stdout.write(
                        "No tests available for the resource %s \n"
                        % resource_id)

                for configuration in allowed_config:
                    (mode, file_system) = configuration
                    sys.stdout.write(
                        "\n---------------------------------------\n")
                    sys.stdout.write("Mode : " + mode + '\n')
                    sys.stdout.write("File system : " + file_system + '\n')
                    cls.setup_path_management(file_system)

                    suite_list = []
                    list_tests = []
                    for test in dir(cls):
                        prefix = "test_"
                        if len(test) < len(prefix):
                            continue
                        if test[0: len(prefix)] == prefix:
                            list_tests.append(test)

                    suite_list.append(unittest.TestSuite(map(cls,
                                                        list_tests)))
                    alltests = unittest.TestSuite(suite_list)
                    with suppress_stdout(debug):
                        res = unittest.TextTestRunner(verbosity=2).run(
                            alltests)

                    if len(res.errors) != 0 or len(res.failures) != 0:
                        sys.exit(1)

            finally:
                os.unlink(config._database_file)

    @staticmethod
    def parse_args(argv):
        kwargs = {}
        if len(argv) > 1:
            if '--interactive' in argv[1:]:
                kwargs['interactive'] = True
        return kwargs

    def print_job_io_info(self, job_id, msg=None, file=sys.stderr):
        # this debug info should be removed when we find
        # out why tests randomly fail from time to time.
        (jobs_info, transfers_info, workflow_status, workflow_queue,
            tmp_files) = self.wf_ctrl.workflow_elements_status(self.wf_id)
        job_list = self.wf_ctrl.jobs([job_id])
        job_name, job_command, job_submission_date = job_list[job_id]

        print >> file, '\n** failure in %s job stdout/stderr **' \
            % self.__class__.__name__
        if msg:
            print >> file, msg
        eng_stdout, eng_stderr = \
            self.wf_ctrl._engine_proxy.stdouterr_file_path(job_id)
        print >> file, 'job:', job_name, \
            ', stdout:', eng_stdout
        print >> file, open(eng_stdout).read()
        jobs_files = [
            (ji[0],
             self.wf_ctrl._engine_proxy.stdouterr_file_path(ji[0]))
            for ji in jobs_info]
        print >> file, 'engine jobs files:', jobs_files
        print >> file, '** **'

    def assertTrue(self, condition, msg=None):
        if not bool(condition) and hasattr(self, 'tested_job'):
            self.print_job_io_info(self.tested_job, msg)
        return super(WorkflowTest, self).assertTrue(condition, msg)

    def assertFalse(self, condition, msg=None):
        if bool(condition) and hasattr(self, 'tested_job'):
            self.print_job_io_info(self.tested_job, msg)
        return super(WorkflowTest, self).assertFalse(condition, msg)

    def assertEqual(self, first, second, msg=None):
        if first != second and hasattr(self, 'tested_job'):
            self.print_job_io_info(self.tested_job, msg)
        return super(WorkflowTest, self).assertEqual(first, second, msg)

    def assertNonEqual(self, first, second, msg=None):
        if first == second and hasattr(self, 'tested_job'):
            self.print_job_io_info(self.tested_job, msg)
        return super(WorkflowTest, self).assertNonEqual(first, second, msg)

