# coding: utf-8
# © 2015 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import http
from openerp.http import request


class RunbotRenderLogs(http.Controller):

    @http.route(['/logs/<build_id>'], type='http', auth="public", website=True)
    def index_logs(self, build_id=None, **kw):
        registry = request.registry
        cr = request.cr
        uid = request.uid
        build_obj = registry['runbot.build']
        build = build_obj.browse(cr, uid, [int(build_id)])[0]
        if not build.exists():
            return request.not_found()
        logs_site = "http://logs.%s.%s" % (build.dest, build.host)
        return request.redirect(logs_site)
