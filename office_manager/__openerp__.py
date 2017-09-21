# -*- coding: utf-8 -*-
{
    'name': "Office Manager",

    'summary': """
        建立新员工，入职建立邮箱账号，开通加密
        离职员工，归档res_user，hr_employee，删除邮箱与加密
        """,

    'description': """
        入职离职
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
     'views/approvers.xml',
     'views/employee.xml',
     'views/menus.xml',
     'views/recruitment.xml',
     'views/template.xml'
    ],
    'demo': [
        # 'demo/demo.xml',
        ],
    'qweb': ['static/src/xml/button.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}