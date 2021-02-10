# -*- coding: utf-8 -*-
{
    'name': "YDS Security",

    'summary': """
        YDS Security v14.0""",

    'description': 'Contains access rights/ Secuirty enhancement to mrp/inv/sales/accounting/purchase groups',

    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Security',
    'version': '90.1',
    'license': 'LGPL-3',
    'depends': ['mrp','yds_discounts'],

    'data': [
        'security/ir.model.access.csv',
        'security/groups_security.xml',
        'security/record_rules.xml',
        'views/yds_sale_view_security.xml',
        'views/user_view_secuirty.xml'
        
    ],

}
