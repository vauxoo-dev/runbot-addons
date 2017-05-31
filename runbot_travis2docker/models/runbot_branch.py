# coding: utf-8
# © 2015 Vauxoo
#   Coded by: moylop260@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

import requests
import subprocess

from openerp import fields, models, api


class RunbotBranch(models.Model):
    _inherit = "runbot.branch"

    uses_weblate = fields.Boolean(help='Synchronize with Weblate')
    name_weblate = fields.Char(compute='_compute_name_weblate', store=True)

    @api.multi
    @api.depends('repo_id.name', 'branch_name', 'uses_weblate')
    def _compute_name_weblate(self):
        for branch in self:
            name = branch.repo_id.name.replace(':', '/')
            name = re.sub('.+@', '', name)
            name = re.sub('.git$', '', name)
            name = re.sub('^https://', '', name)
            name = re.sub('^http://', '', name)
            match = re.search(
                r'(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+)', name)
            if match:
                name = ("%(host)s:%(owner)s/%(repo)s (%(branch)s)" %
                        dict(match.groupdict(), branch=branch['branch_name']))
            branch.name_weblate = name

    @api.model
    def cron_weblate(self):
        for branch in self.search([('uses_weblate', '=', True)]):
            if (not branch.repo_id.weblate_token or
                    not branch.repo_id.weblate_url):
                continue
            cmd = ['git', '--git-dir=%s' % branch.repo_id.path]
            url = branch.repo_id.weblate_url
            session = requests.Session()
            session.headers.update({
                'Accept': 'application/json',
                'User-Agent': 'runbot_travis2docker',
                'Authorization': 'Token %s' % branch.repo_id.weblate_token
            })
            projects = []
            page = 1
            while True:
                response = session.get('%s/projects/?page=%s' % (url, page))
                response.raise_for_status()
                data = response.json()
                projects.extend(data['results'] or [])
                if not data['next']:
                    break
                page += 1
            for project in projects:
                response = session.get('%s/projects/%s/components'
                                       % (url, project['slug']))
                response.raise_for_status()
                components = response.json()
                updated_branch = None
                for component in components['results']:
                    if (updated_branch and
                            updated_branch == component['branch']):
                        continue
                    if component['branch'] != branch['branch_name']:
                        continue
                    if project['name'] != branch.name_weblate:
                        continue
                    has_build = self.env['runbot.build'].search(
                        [('branch_id', '=', branch.id),
                         ('state', 'in', ('pending', 'running', 'testing')),
                         ('name', '=', component['branch']),
                         ('uses_weblate', '=', True)])
                    if has_build:
                        continue
                    remote = 'wl-%s' % project['slug']
                    url_repo = (branch.repo_id.weblate_url.replace('api',
                                                                   'git') +
                                '/' + project['slug'] + '/' +
                                component['slug'])
                    try:
                        subprocess.check_output(cmd + ['remote', 'add', remote,
                                                url_repo])
                    except subprocess.CalledProcessError:
                        pass
                    subprocess.check_output(cmd + ['fetch', remote])
                    diff = subprocess.check_output(
                        cmd + ['diff',
                               '%(branch)s..%(remote)s/%(branch)s'
                               % {'branch': branch['branch_name'],
                                  'remote': remote}, '--stat'])
                    if not diff:
                        continue
                    self._create_build(branch)
                    updated_branch = component['branch']

    @api.multi
    def force_weblate(self):
        for record in self:
            self._create_build(record)

    def _create_wl_build(self, branch):
        self.env['runbot.build'].create({
            'branch_id': branch.id,
            'name': branch.branch_name,
            'uses_weblate': True})

    def _get_branch_quickconnect_url(self, cr, uid, ids, fqdn, dest,
                                     context=None):
        """Remove debug=1 because is too slow
        Remove database default name because is used openerp_test from MQT
        """
        res = super(RunbotBranch, self)._get_branch_quickconnect_url(
            cr, uid, ids, fqdn, dest, context=context)
        for branch in self.browse(cr, uid, ids, context=context):
            if branch.repo_id.is_travis2docker_build:
                dbname = "db=%s-all&" % dest
                res[branch.id] = res[branch.id].replace(dbname, "").replace(
                    "?debug=1", "")
        return res
