# -*- coding: utf-8 -*-
{
    'name': "managercenter",

    'summary': """
        学生中心管理""",

    'description': """
        学生管理、班级、考勤、就业
    """,

    'author': "Robin Wu",
    'website': "http://www.harmonywin.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'harmonywin',
    'version': '2.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
				'sale',
				'hr',
				'mail',
		],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/classto.xml',
        'views/menus.xml',
        'views/actions.xml',
        'views/course.xml',
        'views/evaluate.xml',
        'views/coreto.xml',
		'views/wizard.xml',
		'wizard/wizard.xml',
        'security/security.xml',
		'demo/demo.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo.xml',
    ],
     'application':True,
     'installable':True,
     'auto_install': False,
}




