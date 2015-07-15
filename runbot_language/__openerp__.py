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
    'description': "Runbot with posibility to indicate the language"
                   " in the instances generated",
    'author': 'Vauxoo',
    'depends': ['runbot'],
    'data': [
        'view/runbot_language_view.xml',
    ],
    'installable': True,
}
