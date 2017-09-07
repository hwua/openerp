# -*- coding: utf-8 -*-
{
    'name': "ClassAndEmploymentMail",
    
    'description': """定时发送客户发送欢迎进班邮件、就业邮件""",

    'author': "Winton.he",
    'website': "http://www.harmonywin.com",

    'category': 'harmonywin',
    'version': '0.1',

    'depends': [
        'mail',
        'Employment',
    ],

    'data': [
    'views/partner_mail_wizard.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
        ],
}