#-*- coding:utf-8 -*-

import logging

from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class SurveyQuestion(osv.Model):
    _inherit = 'survey.question'

    _columns = {
        'question_html': fields.html(string=u'特殊标题')
    }

class SurveySurvey(osv.Model):
    _inherit = 'survey.survey'

    _columns = {
        'disposable': fields.boolean(string=u'一次性调查')
    }

    _defaults = {
        'users_can_go_back': True,
        'auth_required': True,
        'disposable': True,
    }

class SurveUserInput(osv.Model):
    _inherit = "survey.user_input"

    def _quizz_get_score(self, cr, uid, ids, name, args, context=None):
        ret = dict()
        for user_input in self.browse(cr, uid, ids, context=context):
                sn = 0.0
                user_option = {}#选择的成绩
                
                for uil in user_input.user_input_line_ids:
                    if (uil.question_id.type == 'multiple_choice'):
                        # 已回答的题目和用户选项
                        if not user_option.has_key(uil.question_id.id):
                            user_option[uil.question_id.id] = []
                        user_option[uil.question_id.id].append(uil.value_suggested.id)

                    else:
                        sn += uil.quizz_mark

                if user_option:
                    for (question, labels) in user_option.items():
                        right = self.pool.get('survey.label').search(cr, uid, [('question_id', '=', question), ('quizz_mark','>',0.0)], None)# 此题的正确选项
                        wrong = list(set(labels).difference(set(right)))# 用户选择的错误选项

                        if wrong == []and right == labels:#无错，正确值和题目正确值相同，即合计分数
                            survey_labels = self.pool.get('survey.label').browse(cr, uid, labels)
                            sn += sum([sl.quizz_mark for sl in survey_labels] or [0.0])

                ret[user_input.id] = sn

        return ret

    _columns = {
        'quizz_score': fields.function(_quizz_get_score, type="float", string="Score for the quiz")
    }