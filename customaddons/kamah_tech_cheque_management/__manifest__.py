# -*- coding: utf-8 -*-
{
    'name': "Check Management",

    'sequence': '100',

    'summary': """ Check Management  """,

    'description': """
        This Module is used for check \n
        It includes creation of check receipt ,check cycle ,Holding ....... \n

    """,

    'author': "YDS Digital Solutions",
    'website': "http://www.yds-int.com/",

    # Categories can be used to filter modules in modules listing
    # Check
    # for the full list
    'category': 'Accounting',
    'version': '14.0.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_accountant', 'yds_discounts'],

    # always loaded
    'data': [

        'security/ir.model.access.csv',
        'security/checks_security.xml',
        'views/account_journal_view.xml',
        'views/checks_fields_view.xml',
        'views/check_payment.xml',
        'views/check_menus.xml',
        'wizard/check_cycle_wizard_view.xml',
        'views/payment_report.xml',
        'views/report_check_cash_payment_receipt_templates.xml',
        'views/res_config.xml',
        # 'data/sms_temp.xml',

    ],
    'qweb': [],
    # only loaded in demonstration mode
    'demo': [],
    'license': 'GPL-3',
    'price': 200.0,
    'currency': 'EUR',
    'application': True,

}
