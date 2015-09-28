# coding: utf-8
from openerp import fields, models
from openerp.addons.runbot_build_instructions.runbot_build \
    import MAGIC_PID_RUN_NEXT_JOB
from openerp.addons.runbot import mkdirs, run


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
            regular_func = getattr(super(runbot_build, self), func.func_name)
            ret = regular_func(cr, uid, regular_ids, context=context)
        if custom_ids:
            assert ret is None
            ret = func(self, cr, uid, custom_ids, context=context)
        return ret
    return custom_func


class RunbotBuild(models.Model):
    _inherit = 'runbot.build'

    def job_00_init(self, cr, uid, build, lock_path, log_path):
        if build.branch_id.repo_id.is_travis2docker_build:
            _logger.info('skipping job_00_init')
            return MAGIC_PID_RUN_NEXT_JOB
        return super(runbot_build, self).job_00_init(
            cr, uid, build, lock_path, log_path)

    def job_10_test_base(self, cr, uid, build, lock_path, log_path):
        if build.branch_id.repo_id.is_travis2docker_build:
            _logger.info('skipping job_10_test_base')
            return MAGIC_PID_RUN_NEXT_JOB
        return super(runbot_build, self).job_10_test_base(
            cr, uid, build, lock_path, log_path)

    @custom_build
    def checkout(self, cr, uid, ids, context=None):
        """Save travis2docker output"""
        # runbot log path
        import pdb;pdb.set_trace()
        for build in self.browse(cr, uid, ids, context=context):
            run(['travisfile2dockerfile', build.repo_id.name, build.name])
    #TODO: Add custom build to drop and kill


