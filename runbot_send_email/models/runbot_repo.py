from odoo import models


class RunbotRepo(models.Model):

    _name = 'runbot.repo'
    _inherit = ['runbot.repo', 'mail.thread']

    def update_followers(self):
        """This method remove or add the user from followers of model
        'runbot.repo' that has logged, also the method update the followers
        builds that are relation with the repository.
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        builds = self.env['runbot.build'].search([('repo_id', '=', self.id)])
        if partner not in self.message_partner_ids:
            self.message_subscribe_users(user_ids=[self.env.uid])
            follower = True
        else:
            self.message_unsubscribe_users(user_ids=[self.env.uid])
            follower = False
        method_name = 'message_{}subscribe_users'.format(
            '' if follower else 'un')
        for build in builds:
            if (partner in build.message_partner_ids and
                    follower) or not hasattr(build, method_name):
                continue
            method = getattr(build, method_name)
            method(user_ids=[self.env.uid])
        return follower
