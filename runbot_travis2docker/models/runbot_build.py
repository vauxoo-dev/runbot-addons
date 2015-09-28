# coding: utf-8

import logging
import os
import sys

from openerp import fields, models
from openerp.addons.runbot_build_instructions.runbot_build \
    import MAGIC_PID_RUN_NEXT_JOB
from openerp.addons.runbot.runbot import mkdirs, run

from travis2docker.travis2docker import main as t2d

_logger = logging.getLogger(__name__)


def custom_build(func):
    # TODO: Make this method more generic for re-use in all custom modules
    """Decorator for functions which should be overwritten only if
    is_travis2docker_build is enabled in repo.
    """
    def custom_func(self, cr, uid, ids, context=None):
        args = [
            ('id', 'in', ids),
            ('branch_id.repo_id.is_travis2docker_build', '=', True)
        ]
        custom_ids = self.search(cr, uid, args, context=context)
        regular_ids = list(set(ids) - set(custom_ids))
        ret = None
        if regular_ids:
            regular_func = getattr(super(RunbotBuild, self), func.func_name)
            ret = regular_func(cr, uid, regular_ids, context=context)
        if custom_ids:
            assert ret is None
            ret = func(self, cr, uid, custom_ids, context=context)
        return ret
    return custom_func


class RunbotBuild(models.Model):
    _inherit = 'runbot.build'

    dockerfile_path = fields.Char()

    def job_10_test_base(self, cr, uid, build, lock_path, log_path):
        if build.branch_id.repo_id.is_travis2docker_build:
            _logger.info('skipping job_10_test_base')
            return MAGIC_PID_RUN_NEXT_JOB
        return super(RunbotBuild, self).job_10_test_base(
            cr, uid, build, lock_path, log_path)

    def job_20_test_all(self, cr, uid, build, lock_path, log_path):
        if not build.branch_id.repo_id.is_travis2docker_build:
            return super(RunbotBuild, self).job_20_test_all(
                cr, uid, build, lock_path, log_path)
        if not build.dockerfile_path:
            _logger.info(
                'skipping job_20_test_all: '
                'Dockerfile without TESTS=1 env')

            return MAGIC_PID_RUN_NEXT_JOB
        print build.dockerfile_path
        raise NotImplemented("ToDo: Run travis container expose "
                             "port 8069 to build port")

    @custom_build
    def checkout(self, cr, uid, ids, context=None):
        """Save travis2docker output"""
        for build in self.browse(cr, uid, ids, context=context):
            branch_short_name = build.branch_id.name.replace(
                'refs/heads/', '', 1).replace('refs/pull/', '', 1)
            t2d_path = os.path.join(build.repo_id.root(), 'travis2docker')
            sys.argv = [
                'travisfile2dockerfile', build.repo_id.name,
                branch_short_name, '--root-path=' + t2d_path]
            path_scripts = t2d()
            for path_script in path_scripts:
                df_content = open(os.path.join(
                    path_script, 'Dockerfile')).read()
                if 'ENV TESTS=1' in df_content:
                    build.dockerfile_path = path_script

    # TODO: Add custom_build to drop and kill
