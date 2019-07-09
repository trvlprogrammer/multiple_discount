# -*- coding: utf-8 -*-
{
    'name': "Multiple Discount For Sale & Invoice",

    'summary': """
        Multiple discount in sale and invoicing""",

    'description': """
        This module inherit sale and account to add new feature called multiple discount.
        If you need customization odoo you can email me at alfatihridhont@gmail.com
    """,

    'author': "Alfant Projects",
    'website': "alfatihridhont@gmail.com",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['base','sale_management'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
    ],
}