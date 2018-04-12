# Copyright <2016> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import os
import threading

from odoo import exceptions
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


class TestRunbotSendEmail(TransactionCase):
    """
    This create a runbot send email test
    """

    def setUp(self):
        """
        This add required environment variable for test
        """
        super(TestRunbotSendEmail, self).setUp()
        repo_name = 'https://github.com/owner/repo_name.git'
        branch_name = 'refs/heads/branch_name'
        self.repo_obj = self.env['runbot.repo'].create({
            'name': repo_name,
            'modules_auto': 'repo',
            'mode': 'poll',
            'nginx': True,
        })
        self.branch_obj = self.env['runbot.branch'].create({
            'repo_id': self.repo_obj.id,
            'name': branch_name,
            'branch_name': 'branch_name',
            'sticky': False,
            'coverage': False,
        })
        recipient = os.environ.get('EMAIL_RECIPIENT', 'committer@testsend.com')
        self.build_obj = self.env['runbot.build'].create({
            'branch_id': self.branch_obj.id,
            'name': 'fcb98eb195fc62fa49873f8f101f1738e38ea7c0',
            'author': 'Test Author',
            'author_email': 'author@testsend.com',
            'committer': 'Test Committer',
            'committer_email': recipient,
            'subject': '[TEST] Test message commit',
            'date': '2016-03-08 00:00:00',
        })
        self.domain = [('repo_id', '=', self.repo_obj.id)]
        self.build = self.build_obj.search(self.domain)
        if os.environ.get('EMAIL_PASSWORD', False) and \
                os.environ.get('EMAIL_RECIPIENT', False) and \
                os.environ.get('EMAIL_USER', False):
            setattr(threading.currentThread(), 'testing', False)
            self.build.pool._init = False
            self.mail_server = self.env.ref(
                'runbot_send_email.runbot_send_ir_mail_server_demo')
            self.mail_server.write({
                'smtp_pass': os.environ.get('EMAIL_PASSWORD'),
                'smtp_user': os.environ.get('EMAIL_USER'),
                'sequence': 0,
            })

    def tearDown(self):
        """
        This method is overwrite because
        we need to reset values of setUp methods
        """
        super(TestRunbotSendEmail, self).tearDown()
        setattr(threading.currentThread(), 'testing', True)
        self.build.pool._init = True

    def test_10_test_connection(self):
        """
        This makes the test smtp conection if EMAIL_PASSWORD env is set
        """
        if os.environ.get('EMAIL_PASSWORD', False) and \
                os.environ.get('EMAIL_RECIPIENT', False) and \
                os.environ.get('EMAIL_USER', False):
            with self.assertRaisesRegex(exceptions.except_orm,
                                        'Connection Test Succeeded!'):
                self.mail_server.test_smtp_connection()

    def test_20_send_email(self):
        """
        This test tries to send a runbot email with password
        """
        self.build._github_status()

    def test_30_send_email_result_ok(self):
        self.build = self.build.search(self.domain)
        self.build.write({'result': 'ok', 'state': 'done'})
        self.build._github_status()

    def test_30_send_email_result_ko(self):
        self.build = self.build.search(self.domain)
        self.build.write({'result': 'ko'})
        self.build._github_status()

    def test_30_send_email_result_warn(self):
        self.build = self.build.search(self.domain)
        self.build.write({'result': 'warn', 'state': 'done'})
        self.build._github_status()

    def test_40_send_email_state_testing(self):
        self.build = self.build.search(self.domain)
        self.build.write({'state': 'testing'})
        self.build._github_status()

    def test_50_send_email_brach_pr(self):
        self.branch_obj.write({'name': 'refs/pull/1'})
        self.build = self.build.search(self.domain)
        self.build._github_status()

    def test_60_coverage_value_error_form(self):
        self.env.ref('mail.email_compose_message_wizard_form').unlink()
        self.build._github_status()

    def test_70_coverage_value_error_template(self):
        self.env.ref('runbot_send_email.runbot_send_notif').unlink()
        self.build._github_status()

    def test_80_user_follow_unfollow_runbot_build(self):
        """Test for the method user_follow_unfollow for the model runbot.build.
        """
        user = self.env['res.users'].browse(self.env.uid)
        result = self.build.user_follow_unfollow()
        followers = self.build.message_partner_ids
        self.assertFalse(result)
        self.assertFalse(followers)
        result = self.build.user_follow_unfollow()
        followers = self.build.message_partner_ids
        self.assertTrue(result)
        self.assertEquals(user.partner_id, followers[0])

    def test_81_user_follow_unfollow_runbot_repo(self):
        """Test for the method user_follow_unfollow for the model runbot.repo.
        """
        user = self.env['res.users'].browse(self.env.uid)
        result = self.build.repo_id.user_follow_unfollow()
        self.assertFalse(result)
        self.assertFalse(self.build.repo_id.message_partner_ids)
        result = self.build.repo_id.user_follow_unfollow()
        followers = self.build.repo_id.message_partner_ids
        self.assertTrue(result)
        self.assertEquals(user.partner_id, followers[0])
        self.assertEquals(user.partner_id, self.build.message_partner_ids[0])

    def test_82_message_get_email_values(self):
        """Test for the method message_get_email_values.
        """
        result = self.build.message_get_email_values()
        emails = self.build.message_partner_ids.mapped('email')
        self.assertTrue(result)
        self.assertEquals(','.join(emails), result.get('email_to'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_90_send_email(self):
        """Test for the method send_email_admins.
        """
        self.build.send_email()
        mail = self.env['mail.mail'].search([('res_id', '=', self.build.id)],
                                            limit=1, order='id desc')
        emails = self.build.message_partner_ids.mapped('email')
        self.assertTrue(mail)
        self.assertTrue(mail.body)
        self.assertEqual(','.join(emails), mail.email_to)
