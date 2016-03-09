# coding: utf-8
# © 2016 Vauxoo
#   Coded by: lescobar@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "runbot_render_logs",
    'summary': """
    This module add a live logs of runbot builds.
        """,
    'author': "Vauxoo, Odoo Community Association (OCA)",
    'website': "https://www.vauxoo.com",
    'category': 'runbot',
    'version': '0.1',
    'depends': ['base', 'runbot', 'runbot_travis2docker'],
    "external_dependencies": {
        "python": [ 'travis2docker', ],
        "bin": [ 'docker', ],
    },
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'data/runbot_render_logs_data.xml',
    ],
    'demo': [
    ],
}
