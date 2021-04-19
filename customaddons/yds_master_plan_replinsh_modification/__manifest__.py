# -*- coding: utf-8 -*-
{
    'name': "YDS Master Plan Replinsh Modification",

    'summary': """
        Modify MRP master production schedule to creat MO with state draft 
        instead of state confirmed""",


    'author': "YDS",
    'website': "http://www.ys-int.com",

    
    'category': 'YDS',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp', 'mrp_mps'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
