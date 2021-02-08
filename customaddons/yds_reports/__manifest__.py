# -*- coding: utf-8 -*-
{
    'name': "YDS Report",

    'summary': """
        YDS Reports v14.0""",

    'description': 'Account, Sales and MRP reports modifications by YDS',

    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Sales',
    'version': '90.1',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'purchase', 'account','mrp','yds_discounts','yds_mrp2','product','percent_field'],

    'data': [
        'security/ir.model.access.csv',
        'wizards/mrp_report_wizard.xml',
        'reports/mrp_report.xml',
        'reports/mrp_report_view.xml',
        # 'reports/yds_cost_structure_report.xml',
        # 'views/include_js.xml',
    ],

}
