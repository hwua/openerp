# -*- coding: utf-8 -*-
{
    'name': "Office Manager",

    'summary': """
        """,

    'description': """
        入职管理
    """,

    'author': "Winton.he",
    'website': "http://www.harmonywin.com",

    'category': 'harmonywin',
    'version': '0.1',

    'depends': [
    'survey',
    'investigation',
    'auth_ldap',
    'hr_contract',
    'hr_employee_expend',
    'Recruitment',
    ],
    'data': [
     'views/department.xml',
     'views/approvers.xml',
     'views/employee.xml',
     'views/menus.xml',
     'views/library_view.xml',
     'views/recruitment.xml'
    ],
    'demo': [
        # 'demo/demo.xml',
        ],
    'qweb': ['static/src/xml/button.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}