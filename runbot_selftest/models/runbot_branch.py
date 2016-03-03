# -*- coding: utf-8 -*-
# © 2015 Vauxoo
# Coding by Moises Lopez <moylop260@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


# class RunbotBranch(models.Model):
#     _inherit = "runbot.branch"

#     # pr_ok = fields.Boolean('Is pull request?',
#     #                        compute='_compute_git_data', store=True)
#     # branch_base_id = fields.Many2one('runbot.branch', string='Branch Base',
#     #                                  compute='_compute_git_data', store=True)

#     @api.depends('name')
#     def _compute_git_data(self):
#         # The main method to get closest branch is in repo.build model :(
#         build = self.env['runbot.build']
#         for branch in self:
#             # Method `create` of runbot.build is inherited returning None :(
#             self.env.cr.execute('SAVEPOINT "build_dummy"')
#             build.create(
#                 {'branch_id': branch.id, 'name': 'dummy'})
#             build_dummy = build.search([
#                 ('branch_id', '=', branch.id), ('name', '=', 'dummy')],
#                 limit=1, order='id desc')
#             repo_id, closest_name, server_match = \
#                 build_dummy._get_closest_branch_name(branch.repo_id.id)
#             self.env.cr.execute('ROLLBACK TO SAVEPOINT "build_dummy"')
#             branch_base = self.search([
#                 ('repo_id', '=', repo_id), ('name', '=', closest_name)],
#                 limit=1)
#             if branch_base.id and branch_base.id != branch.id:
#                 branch.branch_base_id = branch_base.id
#                 branch.pr_ok = True
