# coding: utf-8
# © 2015 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
import signal

from openerp.addons.runbot.runbot import run, mkdirs

from openerp.tools import config

from openerp import models

_logger = logging.getLogger(__name__)


class RunbotRepo(models.Model):
    _inherit = 'runbot.repo'

    def reload_nginx(self, cr, uid, context=None):
        """
        This method is overridden because the original only does the search
        for the build in state = running, but is required to also search the
        build in state = testing
        """
        settings = {}
        settings['port'] = config['xmlrpc_port']
        nginx_dir = os.path.join(self.root(cr, uid), 'nginx')
        settings['nginx_dir'] = nginx_dir
        ids = self.search(cr, uid, [('nginx', '=', True)], order='id')
        if ids:
            # Here the code was changed
            build_ids = self.pool['runbot.build'].search(cr, uid,
                                                         [('repo_id',
                                                           'in', ids),
                                                          ('state', 'in',
                                                           ['running',
                                                            'testing'])])
            # Original code
            # ## build_ids = self.pool['runbot.build'].search(cr, uid,
            # ##      [('repo_id','in',ids), ('state','=','running')])
            settings['builds'] = self.pool['runbot.build'].browse(cr, uid,
                                                                  build_ids)

            nginx_config = self.pool['ir.ui.view']\
                .render(cr, uid, "runbot.nginx_config", settings)
            mkdirs([nginx_dir])
            open(os.path.join(nginx_dir, 'nginx.conf'), 'w')\
                .write(nginx_config)
            try:
                _logger.debug('reload nginx')
                pid = int(open(os.path.join(nginx_dir, 'nginx.pid')).read()
                          .strip(' \n'))
                os.kill(pid, signal.SIGHUP)
            except Exception:
                _logger.debug('start nginx')
                if run(['/usr/sbin/nginx', '-p', nginx_dir, '-c',
                        'nginx.conf']):
                    # obscure nginx bug leaving orphan worker listening on
                    # nginx port
                    if not run(['pkill', '-f', '-P1', 'nginx: worker']):
                        _logger.debug('failed to start nginx - orphan worker \
                                      killed, retrying')
                        run(['/usr/sbin/nginx', '-p', nginx_dir, '-c',
                             'nginx.conf'])
                    else:
                        _logger.debug('failed to start nginx - failed to kill \
                                      orphan worker - oh well')
