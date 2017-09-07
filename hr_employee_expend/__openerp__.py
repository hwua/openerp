# -*- coding: utf-8 -*-
{
    'name': "HR Employee Expond",

    'summary': """
        """,

    'description': """
        员工添加社保信息，工资信息，
    """,

    'author': "Winton.he",
    'website': "http://www.harmonywin.com",

    'category': 'harmonywin',
    'version': '0.1',

    'depends': [
    'hr_contract',
    ],
    'data': [
     'views/centercompany.xml',
     'views/shebaofuction.xml',
     'views/employee.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}