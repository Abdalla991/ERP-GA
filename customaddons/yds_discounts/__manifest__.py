# -*- coding: utf-8 -*-
{
    'name': "YDS Discounts",

    'summary': """
        Modification to discounts in Sales and Accounting by YDS
        """,

    'description': """
        -Seperates discount value from subtotal and a new item in Journal items
        -Adds a new "Universal Discount" field """,

    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Sales Management',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'purchase', 'sale_management','account','mrp','sale_margin'],

    'data': [
        'views/yds_pricelist_view.xml',
        'views/sale_extension.xml',
        'views/invoice_extension.xml',
        'views/yds_pricelist_invoice.xml',
        'report/sale_report_templates.xml',
        'report/yds_purchase_report.xml',
        'report/purchase_importing_po.xml',
        'views/report_invoice.xml',
        'views/ks_sale_order.xml',
        'views/ks_account_invoice.xml',
        'views/ks_account_invoice_supplier_form.xml',
        'views/ks_account_account.xml',
        'views/ks_report.xml',
        'views/yds_res_partner.xml',
        'views/yds_sale_margin.xml',
        'views/assets.xml',
        

    ],

}
