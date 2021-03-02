# -*- coding: utf-8 -*-
{
    'name': "YDS Printing",
    'summary': """
        YDS Printing v14.0
        unhide Chrome print layout field when Ctrl+P.
        """,
    'description':
    'Contains access rights/ Secuirty enhancement to mrp/inv/sales/accounting/purchase groups',
    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Utility',
    'version': '90.1',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
}
