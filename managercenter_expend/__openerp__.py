# -*- coding: utf-8 -*-
{
    'name': "managercenter_expend",

    'summary': """
        教务视图修改""",

    'description': """
        教务视图修改
    """,

    'author': "wenbo du",
    'website': "http://www.harmonywin.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'harmonywin',
    'version': '2.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                # 'sale',
                # 'hr',
                # 'mail',
                'teaching',
                'managercenter',
		],

    # always loaded
    'data': [
        # 'template.xml',
        'views/interview.xml',
        'views/examination.xml',
        'views/examinationstu.xml',
        'views/studentandtest.xml',
        'views/activity.xml',
        'views/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo.xml',
    ],
     'application':True,
     'installable':True,
     'auto_install': False,
}




