# -*- coding: utf-8 -*-
{
    'name': "YDS MRP",

    'summary': """
        YDS MRP v14.0""",

    'description': 'MRP Modifications by YDS',

    'author': "YDS",
    'website': "https://www.yds-int.com/",
    'category': 'Manufactoring',
    'version': '90.1',
    'license': 'LGPL-3',
    'depends': ['mrp','product','percent_field','stock_landed_costs'],

    'data': [
        'views/views.xml',
        'views/mrp_bom_ext.xml',
        'views/mrp_yds_routing_view.xml',
    ],

}
