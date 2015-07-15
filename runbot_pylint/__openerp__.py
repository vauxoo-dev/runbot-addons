# -*- encoding: utf-8 -*-
##############################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2011 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: moylop260@vauxoo.com
############################################################################

{
    'name': 'Runbot Pylint',
    'category': 'Website',
    'summary': 'Runbot',
    'version': '1.0',
    'author': 'Vauxoo, ',
    'depends': ['runbot'],
    'external_dependencies': {
        'bin': ['pylint'],
    },
    'data': [
        "views/runbot_pylint_view.xml",
    ],
    'installable': True,
}
