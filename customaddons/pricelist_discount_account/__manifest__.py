# -*- coding: utf-8 -*-
{
    'name': "Pricelist Discount Account",

    'summary': """
        Pricelist Discount Account v14.0""",

    'description': 'asd',

    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Sales Management',
    'version': '1.2.0',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'purchase', 'sale_management','account','mrp'],

    'data': [
        'views/yds_pricelist_view.xml',
        'views/report_invoice.xml',
        'views/sale_extension.xml',
        'views/invoice_extension.xml',
        'views/yds_pricelist_invoice.xml',
        'report/sale_report_templates.xml',
        'views/mrp_bom_ext.xml',
        'views/ks_sale_order.xml',
        'views/ks_account_invoice.xml',
        'views/ks_purchase_order.xml',
        'views/ks_account_invoice_supplier_form.xml',
        'views/ks_account_account.xml',
        'views/ks_report.xml',
        'views/yds_res_partner.xml',
        'views/assets.xml',
        

    ],

}
