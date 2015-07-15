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
    'name': 'Runbot Language',
    'category': 'Website',
    'summary': 'Runbot',
    'version': '1.1',
    "website": "http://www.vauxoo.com/",
    'author': 'Vauxoo,Odoo Community Association (OCA)',
    'depends': ['runbot'],
    'data': [
        'views/runbot_repo_views.xml',
        'views/runbot_build_views.xml',
    ],
    'installable': True,
}
