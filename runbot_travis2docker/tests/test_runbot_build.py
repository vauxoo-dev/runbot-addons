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
        self.repo_2 = self.env.ref('runbot_travis2docker.runbot_repo_demo2')
        self.repo_domain = [('repo_id', '=', self.repo.id)]
        self.build = None

    def delete_build_path(self, build):
        subprocess.check_output(['rm', '-rf', self.build.path()])

    def delete_image_cache(self, build):
        cmd = ['docker', 'rmi', '-f', self.build.docker_image_cache]
        res = -1
        try:
            res = subprocess.check_output(cmd)
        except subprocess.CalledProcessError:
            pass
        return res

    def delete_container(self, build):
        cmd = ['docker', 'rm', '-f', self.build.get_docker_container()]
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
            if self.build.job != current_job:
                return self.build.job
            time.sleep(timeout)
            if divmod(count + 1, 5)[1] == 0:
                _logger.info("...")
        # The build don't changed of job.
        return False

    def check_registry_service(self):
        pass

    def test_10_jobs_branch(self):
        "Create build and run all jobs in branch case (not pull request)"
        global _logger  # pylint: disable=global-statement
        _logger = logging.getLogger(__name__ + '.def test_10_jobs_branch')
        self.run_jobs('refs/heads/fast-travis')

    def test_20_jobs_pr(self):
        "Create build and run all jobs in pull request"
        global _logger  # pylint: disable=global-statement
        _logger = logging.getLogger(__name__ + '.def test_20_jobs_pr')
        self.run_jobs('refs/pull/1')

    def run_jobs(self, branch):
        self.assertTrue(
            self.exists_container('registry', include_stop=False),
            "A docker container registry is required. Try running: "
            "'docker run -d -p 5000:5000 --name registry registry:2'")
        self.assertEqual(len(self.repo), 1, "Repo not found")
        self.repo.update()
        self.repo.killall()
        branch = self.branch_obj.search(self.repo_domain + [
            ('name', '=', branch)], limit=1)
        self.assertEqual(len(branch), 1, "Branch not found")
        self.build_obj.search([('branch_id', '=', branch.id)]).unlink()
        self.build_obj.create({'branch_id': branch.id, 'name': 'HEAD'})
        # runbot module has a inherit in create method
        # but a "return id" is missed. Then we need to search it.
        # https://github.com/odoo/odoo-extra/blob/038fd3e/runbot/runbot.py#L599
        self.build = self.build_obj.search([('branch_id', '=', branch.id)],
                                           limit=1)
        self.assertEqual(len(self.build) == 0, False, "Build not found")

        if self.build.state == 'done' and self.build.result == 'skipped':
            # When the last commit of the repo is too old,
            # runbot will skip this build then we are forcing it
            self.build.force()

        self.build.checkout()
        self.delete_build_path(self.build)
        self.assertEqual(
            self.build.state, u'pending', "State should be pending")

        self.repo.cron()
        self.assertEqual(
            self.build.state, u'testing', "State should be testing")
        images_result = subprocess.check_output(['docker', 'images'])
        _logger.info(images_result)
        containers_result = subprocess.check_output(['docker', 'ps'])
        _logger.info(containers_result)
        if not self.build.is_pull_request:
            self.assertEqual(
                self.build.job, u'job_10_test_base',
                "Job should be job_10_test_base")
            new_current_job = self.wait_change_job(self.build.job, self.build)
            _logger.info(
                open(os.path.join(self.build.path(), "logs",
                                  "job_10_test_base.txt")).read())
        else:
            self.assertTrue(
                self.docker_registry_test(self.build),
                "Docker image don't found in registry to re-use in PR.",
            )
            new_current_job = u'job_20_test_all'

        self.assertEqual(
            new_current_job, u'job_20_test_all')
        new_current_job = self.wait_change_job(new_current_job, self.build)
        self.assertEqual(
            new_current_job, u'job_30_run',
            "Job should be job_30_run, found %s" % new_current_job)
        _logger.info(open(
            os.path.join(self.build.path(), "logs",
                         "job_20_test_all.txt")).read())

        self.assertEqual(
            self.build.state, u'running',
            "Job state should be running")

        user_ids = self.connection_test(self.build, 36, 10)
        _logger.info(open(
            os.path.join(self.build.path(), "logs",
                         "job_30_run.txt")).read())

        self.assertEqual(
            self.build.state, u'running',
            "Job state should be running still")
        self.assertEqual(
            len(user_ids) >= 1, True, "Failed connection test")

        self.assertEqual(
            self.build.result, u'ok', "Job result should be ok")
        self.assertTrue(
            self.exists_container(self.build.docker_container),
            "Container dont't exists")
        self.build.kill()
        self.assertEqual(
            self.build.state, u'done', "Job state should be done")
        self.assertFalse(
            self.exists_container(self.build.docker_container),
            "Container don't deleted")
        if not self.build.is_pull_request:
            self.assertTrue(
                self.docker_registry_test(self.build),
                "Docker image don't found in registry.",
            )
            self.delete_image_cache(self.build)
        # Runbot original module use cr.commit :(
        # This explicit commit help us to avoid believe
        # that we will have a rollback of the data
        self.cr.commit()  # pylint: disable=invalid-commit

    def exists_container(self, container_name, include_stop=True):
        cmd = ['docker', 'ps']
        if include_stop:
            cmd.append('-a')
        containers = subprocess.check_output(cmd)
        if container_name in containers:
            return True
        return False

    def docker_registry_test(self, build):
        cmd = [
            "curl", "--silent",
            "localhost:5000/v2/"
            "vauxoo-dev-runbot_branch_remote_name_grp_feature2/tags/list",
        ]
        tag_list_output = subprocess.check_output(cmd)
        tag_build = self.build.docker_image_cache.split(':')[-1]
        return tag_build in tag_list_output

    def test_jobs_ci_skip(self):
        """Test the [ci skip] feature"""
        # 'Create build and run all jobs'
        self.assertEqual(len(self.repo), 1, "Repo not found")
        _logger.info("Repo update to get branches")
        self.repo_2.update()

        branch = self.branch_obj.create({
            'repo_id': self.repo_2.id,
            'name': 'refs/heads/fast-travis-oca',
        })
        self.assertEqual(len(branch), 1, "Branch not found")
        self.build_obj.search([('branch_id', '=', branch.id)]).unlink()
        self.build_obj.create({'branch_id': branch.id,
                               'subject': '[CI SKIP] TEST SUBJECT',
                               'name': 'HEAD'})
        # runbot module has a inherit in create method
        # but a "return id" is missed. Then we need to search it.
        # https://github.com/odoo/odoo-extra/blob/038fd3e/runbot/runbot.py#L599
        self.build = self.build_obj.search([('branch_id', '=', branch.id)],
                                           limit=1)
        self.assertEqual(len(self.build) == 0, False, "Build not found")

        if self.build.state == 'done' and self.build.result == 'skipped':
            # When the last commit of the repo is too old,
            # runbot will skip this build then we are forcing it
            self.build.force()

        self.assertEqual(
            self.build.state, u'skipped', "State should be skipped")

        self.build.kill()
        self.assertEqual(
            self.build.state, u'done', "Job state should be done")

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
                _logger.info("Trying connect to build %s %s:%s... failed.",
                             build.sequence, host, port)
            time.sleep(delay)
        return user_ids
