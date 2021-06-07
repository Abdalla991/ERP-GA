# -*- coding: utf-8 -*-
{
    'name': "YDS Partner Ledger Customization",

    'summary': """
        Accounting Partner Ledger Report Customization.
    """,

    'author': "YDS",
    'website': "http://www.yds-int.com",


    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_predictive_bills', 'account_reports'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        #'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
