# coding: utf-8
# © 2015 Vauxoo
#   Coded by: moylop260@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
import subprocess
import time
import xmlrpclib

import openerp
from openerp.tests.common import TransactionCase


_logger = logging.getLogger(__name__)


class TestRunbotJobs(TransactionCase):

    def setUp(self):
        super(TestRunbotJobs, self).setUp()
        self.build_obj = self.env['runbot.build']
        self.repo_obj = self.env['runbot.repo']
        self.branch_obj = self.env['runbot.branch']
        self.repo = self.repo_obj.search([
            ('is_travis2docker_build', '=', True)], limit=1)
        self.repo_domain = [('repo_id', '=', self.repo.id)]

    def delete_build_path(self, build):
        subprocess.check_output(['rm', '-rf', build.path()])

    def delete_image_cache(self, build):
        cmd = ['docker', 'rmi', '-f', build.docker_image_cache]
        res = -1
        try:
            res = subprocess.check_output(cmd)
        except subprocess.CalledProcessError:
            pass
        return res

    def delete_container(self, build):
        cmd = ['docker', 'rm', '-f', build.get_docker_container()]
        res = -1
        try:
            res = subprocess.check_output(cmd)
        except subprocess.CalledProcessError:
            pass
        return res

    @openerp.tools.mute_logger('openerp.addons.runbot.runbot')
    def wait_change_job(self, current_job, build,
                        loops=40, timeout=20):
        _logger.info("Waiting change of current job: %s", current_job)
        for count in range(loops):
            self.repo.cron()
            if build.job != current_job:
                return build.job
            time.sleep(timeout)
            if divmod(count + 1, 5)[1] == 0:
                _logger.info("...")
        # The build don't changed of job.
        return False

    def test_10_jobs_branch(self):
        "Create build and run all jobs in branch case (not pull request)"
        self.run_jobs('refs/head/fast-travis')

    def test_20_jobs_pr(self):
        "Create build and run all jobs in pull request"
        self.run_jobs('refs/pull/1')

    def run_jobs(self, branch):
        self.assertEqual(len(self.repo), 1, "Repo not found")
        self.repo.update()
        branch = self.branch_obj.search(self.repo_domain + [
            ('name', '=', branch)], limit=1)
        self.assertEqual(len(branch), 1, "Branch not found")
        self.build_obj.search([('branch_id', '=', branch.id)]).unlink()

        self.repo.update()
        build = self.build_obj.search([
            ('branch_id', '=', branch.id)], limit=1)
        self.assertEqual(len(build) == 0, False, "Build not found")

        if build.state == 'done' and build.result == 'skipped':
            # When the last commit of the repo is too old,
            # runbot will skip this build then we are forcing it
            build.force()

        build.checkout()
        self.delete_build_path(build)
        self.assertEqual(
            build.state, u'pending', "State should be pending")

        self.repo.cron()
        self.assertEqual(
            build.state, u'testing', "State should be testing")
        if not build.is_pull_request:
            self.assertEqual(
                build.job, u'job_10_test_base',
                "Job should be job_10_test_base")
            new_current_job = self.wait_change_job(build.job, build)
            _logger.info(
                open(os.path.join(build.path(), "logs",
                                  "job_10_test_base.txt")).read())
        else:
            new_current_job = u'job_20_test_all'

        self.assertEqual(
            new_current_job, u'job_20_test_all')
        new_current_job = self.wait_change_job(new_current_job, build)
        _logger.info(open(
            os.path.join(build.path(), "logs",
                         "job_20_test_all.txt")).read())

        self.assertEqual(
            new_current_job, u'job_30_run',
            "Job should be job_30_run")
        self.assertEqual(
            build.state, u'running',
            "Job state should be running")

        user_ids = self.connection_test(build, 36, 10)
        _logger.info(open(
            os.path.join(build.path(), "logs",
                         "job_30_run.txt")).read())

        self.assertEqual(
            build.state, u'running',
            "Job state should be running still")
        self.assertEqual(
            len(user_ids) >= 1, True, "Failed connection test")

        self.assertEqual(
            build.result, u'ok', "Job result should be ok")
        self.assertTrue(
            self.exists_container(build), "Container dont't exists")
        build.kill()
        self.assertEqual(
            build.state, u'done', "Job state should be done")
        self.assertFalse(
            self.exists_container(build), "Container don't deleted")
        if not build.is_pull_request:
            self.assertTrue(
                self.docker_registry_test(build),
                "Docker image don't found in registry.",
            )
            self.delete_image_cache(build)

    def exists_container(self, build):
        cmd = ['docker', 'ps']
        containers = subprocess.check_output(cmd)
        if build.get_docker_container() in containers:
            return True
        return False

    def docker_registry_test(self, build):
        cmd = [
            "curl", "--silent",
            "localhost:5000/v2/"
            "vauxoo-dev-runbot_branch_remote_name_grp_feature2/tags/list",
        ]
        tag_list_output = subprocess.check_output(cmd)
        tag_build = build.docker_image_cache.split(':')[-1]
        return tag_build in tag_list_output

    def connection_test(self, build, attempts=1, delay=0):
        username = "admin"
        password = "admin"
        database_name = "openerp_test"
        port = build.port
        host = '127.0.0.1'
        user_ids = []
        for _ in range(attempts):
            try:
                sock_common = xmlrpclib.ServerProxy(
                    "http://%s:%d/xmlrpc/common" % (host, port))
                uid = sock_common.login(
                    database_name, username, password)
                sock = xmlrpclib.ServerProxy(
                    "http://%s:%d/xmlrpc/object" % (host, port))
                user_ids = sock.execute(
                    database_name, uid, password, 'res.users',
                    'search', [('login', '=', 'admin')])
                _logger.info("Trying connect... connected.")
                return user_ids
            except BaseException:
                _logger.info("Trying connect... failed.")
            time.sleep(delay)
        return user_ids
