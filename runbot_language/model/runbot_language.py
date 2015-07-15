# -*- encoding: utf-8 -*-
##############################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2011 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: moylop260@vauxoo.com
############################################################################

'''
    This file is used to add the field lang in runbot.build and the function
      that install and assign the language to the users in the instance
      generated.
'''

from openerp import fields, models, tools
import logging
from openerp.addons.runbot.runbot import run

_logger = logging.getLogger(__name__)


class RunbotRepo(models.Model):

    '''
    Inherit class runbot_repo to add field to select the language that must
      be assigned to builds
      that generate the repo.
    '''

    _inherit = "runbot.repo"

    lang = fields.Selection(
        tools.scan_languages(), 'Language',
        help='Language to change '
        'instance after of run test.', copy=True),


class RunbotBuild(models.Model):

    '''
    Inherit class runbot_build to add field to select the language &
      the function with a job
      to install and assign the language to users if this is captured
      too is added with an super the
      function create to assign the language from repo in the builds.
    '''

    _inherit = "runbot.build"

    lang = fields.Selection(
        tools.scan_languages(), 'Language',
        help='Language to change '
        'instance after of run test.', copy=True),

    def cmd(self, cr, uid, ids, context=None):
        """Return a list describing the command to start the build"""
        cmd, modules = super(RunbotBuild, self).cmd(
            cr, uid, ids, context=context)
        for build in self.browse(cr, uid, ids, context=context):
            if build.lang and build.job == 'job_30_run':
                cmd.append("--load-language=%s" % (build.lang))
        return cmd, modules

    def update_lang(self, cr, uid, build, context=None):
        """Set lang to all users into '-all' database"""
        if build.lang:
            db_name = "%s-all" % build.dest
            try:
                # update odoo version >=7.0
                run(['psql', db_name, '-c', "UPDATE res_partner SET lang='%s' "
                     "WHERE id IN (SELECT partner_id FROM res_users);" %
                     (build.lang)])
            except BaseException:
                pass
            try:
                # update odoo version <7.0
                run(['psql', db_name, '-c', "UPDATE res_users SET lang='%s';" %
                     (build.lang)])
            except BaseException:
                pass
        return True

    def job_30_run(self, cr, uid, build, lock_path, log_path):
        res = super(RunbotBuild, self).job_30_run(cr, uid, build,
                                                  lock_path, log_path)
        self.update_lang(cr, uid, build)
        return res

    def create(self, cr, uid, values, context=None):
        """
        This method set language from repo in the build.
        """
        if values.get('branch_id', False) and 'lang' not in values:
            branch_pool = self.pool['runbot.branch']
            branch_id = branch_pool.browse(
                cr, uid, values['branch_id'], context=context)
            values.update({
                'lang': branch_id.repo_id.lang,
            })
        return super(RunbotBuild, self).create(cr, uid, values,
                                               context=context)
