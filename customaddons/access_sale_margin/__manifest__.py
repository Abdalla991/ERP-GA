# -*- coding: utf-8 -*-
{
    'name': 'Hide cost and margin in Sale Order',
    'summary': 'Hide sale cost price, hide sale margin price, hide cost, hide margin, hide purchase',
    'description': 'Cost and margin can only be viewed with permission',
    'version': '14.0.1',
    'category': 'Access Right',
    'support': 'info@acruxlab.com',
    # 'price': 2.99,
    # 'currency': 'USD',
    'images': ['static/description/Banner.png'],
    'website': 'https://acruxlab.com',
    'license': 'OPL-1',
    'author': 'AcruxLab',
    'depends': ['sale_margin','yds_discounts'],
    'data': [
        'security/security.xml',
        'views/sale.xml',
    ],
    'application': False,
    'installable': True,
}
