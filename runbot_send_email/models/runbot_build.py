# coding: utf-8
# © 2016 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from urlparse import urlparse

from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)


class RunbotBuild(models.Model):
    _name = "runbot.build"
    _inherit = ['runbot.build', 'mail.thread']

    email_follower = fields.Char(compute='_email_follower')
    host_name = fields.Char(compute='_host_name')
    repo_name = fields.Char(compute='_repo_name')
    branch_name = fields.Char(compute='_branch_name')
    subject_email = fields.Char(compute='_subject_email')
    webaccess_link = fields.Char(compute='_webaccess_link')
    logplainbase_link = fields.Char(compute='_logplainbase_link')
    logplainall_link = fields.Char(compute='_logplainall_link')
    log_link = fields.Char(compute='_log_link')
    ssh_link = fields.Char(compute='_ssh_link')
    doc_link = fields.Char(compute='_doc_link')
    dockerdoc_link = fields.Char(compute='_dockerdoc_link')
    configfile_link = fields.Char(compute='_configfile_link')
    shareissue_link = fields.Char(compute='_shareissue_link')

    @api.multi
    def _email_follower(self):
        for record in self:
            record.email_follower = record.committer_email

    @api.multi
    def _host_name(self):
        ir_config = self.env['ir.config_parameter']
        for record in self:
            base_url = ir_config.get_param('web.base.url')
            record.host_name = urlparse(base_url).hostname

    @api.multi
    def _repo_name(self):
        for record in self:
            descrip = record.repo_id.name.replace('.git', '').replace(
                'https://github.com/', '').replace('/', ' / ')
            record.repo_name = descrip

    @api.multi
    def _branch_name(self):
        for record in self:
            if record.branch_id.name.find("pull") >= 0:
                branch = _(u"PR #{}").format(record.branch_id.branch_name)
            else:
                branch = record.branch_id.branch_name
            record.branch_name = branch

    @api.multi
    def _subject_email(self):
        for record in self:
            status = 'Broken'
            if record.state == 'testing':
                status = 'Testing'
            elif record.state in ('running', 'done'):
                if record.result == 'ok':
                    status = 'Fixed'

            record.subject_email = _(u"[runbot] {}: {} - {} - {}")\
                .format(status, record.dest, record.branch_name,
                        record.repo_name)

    @api.multi
    def _webaccess_link(self):
        for record in self:
            html = "http://{}/?db={}-all"
            link = _(html).format(record.domain, record.dest)
            record.webaccess_link = link

    @api.multi
    def _logplainbase_link(self):
        for record in self:
            html = "http://{}/runbot/static/build/{}/logs/job_10_test_base.txt"
            link = _(html).format(record.host, record.dest)
            record.logplainbase_link = link

    @api.multi
    def _logplainall_link(self):
        for record in self:
            html = "http://{}/runbot/static/build/{}/logs/job_20_test_all.txt"
            link = _(html).format(record.host, record.dest)
            record.logplainall_link = link

    @api.multi
    def _log_link(self):
        for record in self:
            html = "/runbot/build/{}"
            link = _(html).format(record.id)
            record.log_link = link

    @api.multi
    def _ssh_link(self):
        for record in self:
            html = "ssh -p {} root@{}"
            link = _(html).format(record.port+1, record.host_name)
            record.ssh_link = link

    @api.multi
    def _doc_link(self):
        for record in self:
            link = '/runbot_doc/static/index.html'
            record.doc_link = link

    @api.multi
    def _dockerdoc_link(self):
        for record in self:
            link = 'https://github.com/Vauxoo/travis2docker/wiki'
            record.dockerdoc_link = link

    @api.multi
    def _configfile_link(self):
        for record in self:
            link = 'https://github.com/Vauxoo/travis2docker/wiki'
            record.configfile_link = link

    @api.multi
    def _shareissue_link(self):
        for record in self:
            link = 'https://github.com/Vauxoo/runbot-addons/issues/new'
            record.shareissue_link = link

    @api.multi
    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                                                        'runbot_send_email',
                                                        'runbot_send_notif')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'runbot',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def send_email(self):
        for record in self:
            email_to = record.email_follower
            name_build = record.dest
            partner_obj = self.env['res.partner']
            partner_id = partner_obj.find_or_create(email_to)
            partner = partner_obj.browse(partner_id)
            if partner not in record.message_partner_ids:
                record.message_subscribe([partner.id])
            email_act = record.action_send_email()
            if email_act and email_act.get('context'):
                email_ctx = email_act['context']
                record.with_context(email_ctx).message_post_with_template(
                                                    email_ctx.get(
                                                        'default_template_id'))
                _logger.info('Sent email to: %s, Build: %s', email_to,
                             name_build)
        return True

    @api.multi
    def github_status(self):
        super(RunbotBuild, self).github_status()
        self.send_email()
