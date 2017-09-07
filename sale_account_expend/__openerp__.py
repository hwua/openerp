# -*- coding: utf-8 -*-
{
    'name': "sale&account expend loan",
    
    'description': """这是一个销售模块的拓展，在销售和会计的表单中增加贷款方案条目""",

    'author': "Winton.he",
    'website': "http://www.harmonywin.com",

    'category': 'harmonywin',
    'version': '0.1',

    'depends': [
             'base',
             'sale',
             'account'
    ],

    'data': [
    'views/account_loan.xml',
    'views/config_loan_company.xml',
    'views/config_loan_project.xml',
    'views/sale_loan.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
        ],
}