# -*- encoding: utf-8 -*-
##############################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2011 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: moylop260@vauxoo.com
#    planned by: nhomar@vauxoo.com
#                moylop260@vauxoo.com
############################################################################

from openerp import api, models


class Webhook(models.Model):
    _inherit = 'webhook'

    @api.one
    def run_webhook_github_push(self):
        return_res = super(Webhook, self).run_webhook_github_push()
        print "I'm here: runbot run_webhook_github_push"
        return return_res
