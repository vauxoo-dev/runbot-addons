# coding: utf-8
# © 2015 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from openerp.addons.runbot.runbot import run

from openerp import models

_logger = logging.getLogger(__name__)


class RunbotBuild(models.Model):
    _inherit = 'runbot.build'

    def find_port(self, cr, uid):
        """
        This method is overridden to add ports that are used by log.io app
        """
        # currently used port
        ids = self.search(cr, uid, [('state', 'not in', ['pending', 'done'])])
        ports = set(i['port'] for i in self.read(cr, uid, ids, ['port']))

        # starting port
        icp = self.pool['ir.config_parameter']
        port = int(icp.get_param(cr, uid, 'runbot.starting_port',
                                 default=2000))

        # find next free port
        while port in ports:
            # Here the code was changed
            port += 4
            # Original Code
            # ## port += 2

        return port

    def get_logio_image(self, cr, uid):
        icp = self.pool.get('ir.config_parameter')
        image_name = icp.get_param(cr, uid, 'logs.image_name',
                                   default="quay.io/vauxoo/logio")
        return image_name

    def get_logio_container(self, cr, uid, build):
        return "log_%d" % (build.sequence)

    def job_10_test_base(self, cr, uid, build, lock_path, log_path):
        """
        This method is overridden to run the docker of log.io app
        """
        icp = self.pool.get('ir.config_parameter')
        logs_server_port = icp.get_param(cr, uid, 'logs.server_port',
                                         default=28777)
        logs_harvester_port = icp.get_param(cr, uid, 'logs.harvester_port',
                                            default=28778)
        logs_user = icp.get_param(cr, uid, 'logs.user', default="user")
        logs_pass = icp.get_param(cr, uid, 'logs.pass', default="pass")
        logio_container = self.get_logio_container(cr, uid, build)
        run(['docker', 'rm', '-f', logio_container])
        run([
            'docker', 'run', '-d'
            '-e', 'AUTH_USER=' + logs_user,
            '-e', 'AUTH_PASS=' + logs_pass,
            '-v', '%s:%s' % (build.path("logs"), "/logs"),
            '-p', '%s:%s' % (build.port + 2, logs_server_port),
            '-p', '%s:%s' % (build.port + 3, logs_harvester_port),
            '--name=' + logio_container, '-t',
            self.get_logio_image(cr, uid),
        ])
        _logger.info('Run Log.io container' + logio_container)
        res_pid = super(RunbotBuild, self).job_10_test_base(cr, uid, build,
                                                            lock_path,
                                                            log_path)
        return res_pid
