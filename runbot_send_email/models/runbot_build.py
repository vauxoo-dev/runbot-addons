# © 2016 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import re
from urllib.parse import urlparse
from email.utils import formataddr
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class RunbotBuild(models.Model):
    # pylint: disable=method-compute
    _name = "runbot.build"
    _inherit = ['runbot.build', 'mail.thread']

    repo_link = fields.Char()
    pr_link = fields.Char()
    commit_link = fields.Char()
    repo_host = fields.Char()
    repo_owner = fields.Char()
    repo_project = fields.Char()
    status_build = fields.Char(compute='_status_build')
    host_name = fields.Char(compute='_host_name')
    branch_name = fields.Char(compute='_branch_name')
    subject_email = fields.Char(compute='_subject_email')

    @api.multi
    def get_github_links(self):
        repo_git_regex = r"((git@|https://)([\w\.@]+)(/|:))" + \
            r"([~\w,\-,\_]+)/" + r"([\w,\-,\_]+)(.git){0,1}((/){0,1})"
        for rec in self:
            rec.repo_host, rec.repo_owner, rec.repo_project = '', '', ''

            match_object = re.search(repo_git_regex, rec.repo_id.name)
            if match_object:
                rec.repo_host = match_object.group(3)
                rec.repo_owner = match_object.group(5)
                rec.repo_project = match_object.group(6)
            rec.repo_link = "https://" + rec.repo_host + '/' + rec.repo_owner \
                + '/' + rec.repo_project
            rec.pr_link = rec.repo_link + rec.branch_id.name.replace(
                'refs/heads', '/tree').replace('refs', '')
            if (hasattr(rec.branch_id.repo_id, 'uses_gitlab') and
                    rec.branch_id.repo_id.uses_gitlab):
                rec.pr_link = rec.pr_link.replace('/pull/', '/merge_requests/')
            rec.commit_link = rec.repo_link + '/commit/' + rec.name[:8]

    @api.multi
    def _host_name(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            record.host_name = urlparse(base_url).hostname

    @api.multi
    def _branch_name(self):
        for record in self:
            if 'pull' in record.branch_id.name:
                branch = _("%s #{}" % (
                    'PR' if not (
                        hasattr(record.branch_id.repo_id, 'uses_gitlab') and
                        record.branch_id.repo_id.uses_gitlab) else 'MR')
                )
                branch = branch.format(record.branch_id.branch_name)
            else:
                branch = record.branch_id.branch_name
            record.branch_name = branch

    @api.multi
    def _status_build(self):
        for record in self:
            status = 'Broken'
            if record.state == 'testing':
                status = 'Testing'
            elif record.state in ('running', 'done'):
                if record.result == 'ok':
                    status = 'Fixed'
                elif record.result == 'warn':
                    status = "Warning"
            record.status_build = status

    @api.multi
    def _subject_email(self):
        for record in self:
            pr_reg = "(\\/pull\\/)"
            match_pr = re.search(pr_reg, record.branch_id.name)

            if match_pr:
                subject_temp = _("[runbot] {}/{}#{}")\
                    .format(record.repo_owner, record.repo_project,
                            record.branch_id.branch_name)
            else:
                subject_temp = _("[runbot] {}/{}#{} - {}")\
                    .format(record.repo_owner, record.repo_project,
                            record.branch_id.branch_name, record.name[:8])

            record.subject_email = subject_temp

    @api.multi
    def send_email(self):
        config_parameters = self.env['ir.config_parameter'].sudo()
        mail_server = self.env['ir.mail_server'].search(
            [], order='sequence', limit=1)
        partner = self.env['res.partner'].search([
            ('email', '=ilike', self.committer_email)], limit=1)
        email_from = formataddr((partner and partner.name.title or
                                 self.env.user.name.title(),
                                 mail_server.smtp_user or ''))
        reply_to = "{alias}@{domain}".format(
            alias=config_parameters.get_param('mail.catchall.alias'),
            domain=config_parameters.get_param('mail.catchall.domain'))
        emails = self.message_partner_ids.mapped("email")
        if partner and partner not in self.message_partner_ids:
            self.message_subscribe_users(user_ids=[partner.user_ids.id])
        if not emails:
            _logger.warning('Failed to send the email: Receiver not provided')
            return
        values = {'email_from': email_from, 'reply_to': reply_to,
                  'composition_mode': 'mass_mail'}
        template = self.env.ref('runbot_send_email.runbot_send_notif')
        # Render the template
        return self.sudo().message_post_with_template(template.id, **values)

    def _github_status(self):
        build = super(RunbotBuild, self)._github_status()
        for record in self:
            record.get_github_links()
            if record.state == 'running':
                record.send_email()
        return build

    def update_followers(self):
        """This method remove or add the user from followers of model
        'runbot.build' that has logged.
        """
        if self.env.user.partner_id not in self.message_partner_ids:
            self.message_subscribe_users(user_ids=[self.env.uid])
            follower = True
        else:
            self.message_unsubscribe_users(user_ids=[self.env.uid])
            follower = False
        return follower

    def create(self, vals):
        """Add the followers of repository to the followers of build.
        """
        build_id = super(RunbotBuild, self).create(vals)
        users = build_id.repo_id.message_partner_ids.mapped('user_ids')
        build_id.message_subscribe_users(user_ids=users.ids)
        return build_id

    def message_get_email_values(self):
        """Get the values for the
        """
        return {'email_to': ','.join(self.message_partner_ids.mapped('email'))}
