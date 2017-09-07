# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug
import werkzeug.utils
from datetime import datetime
from math import ceil

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT as DTF, ustr

_logger = logging.getLogger(__name__)

class WebsiteSurvey(http.Controller):

    # ## HELPER METHODS ##

    def _check_bad_cases(self, cr, uid, request, survey_obj, survey, user_input_obj, token=None, context=None):
        # In case of bad survey, redirect to surveys list
        if survey_obj.exists(cr, SUPERUSER_ID, survey.id, context=context) == []:
            return werkzeug.utils.redirect("/survey/")

        # In case of auth required, block public user
        if survey.auth_required and uid == request.website.user_id.id:
            return request.website.render("survey.auth_required", {'survey': survey, 'token': token})

        # In case of non open surveys
        if survey.stage_id.closed:
            return request.website.render("survey.notopen")

        # If there is no pages
        if not survey.page_ids:
            return request.website.render("survey.nopages")

        # Everything seems to be ok
        return None

    def _check_deadline(self, cr, uid, user_input, context=None):
        '''Prevent opening of the survey if the deadline has turned out

        ! This will NOT disallow access to users who have already partially filled the survey !'''
        if user_input.deadline:
            dt_deadline = datetime.strptime(user_input.deadline, DTF)
            dt_now = datetime.now()
            if dt_now > dt_deadline:  # survey is not open anymore
                return request.website.render("survey.notopen")

        return None

    #当刷新页面，就会更新token，造成重复调查，所以加入一次性调查功能
    def _check_disposable(self, cr, uid, survey, user_input_obj, context=None):
        if survey.disposable == True:
            result = user_input_obj.search(cr, uid, [('create_uid', '=', uid),('state', '=', 'done'),('survey_id','=',survey.id)])
            if result:
                return request.website.render("investigation.disposable")
        return None

    # Survey displaying
    @http.route(['/survey/fill/<model("survey.survey"):survey>/<string:token>',
                 '/survey/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>'],
                type='http', auth='public', website=True)
    def fill_survey(self, survey, token, prev=None, **post):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        user_input_obj = request.registry['survey.user_input']


        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(cr, uid, request, survey_obj, survey, user_input_obj, context=context)
        if errpage:
            return errpage

        # Load the user_input
        try:
            user_input_id = user_input_obj.search(cr, SUPERUSER_ID, [('token', '=', token)])[0]
        except IndexError:  # Invalid token
            return request.website.render("website.403")
        else:
            user_input = user_input_obj.browse(cr, SUPERUSER_ID, [user_input_id], context=context)[0]

        # Do not display expired survey (even if some pages have already been
        # displayed -- There's a time for everything!)
        errpage = self._check_deadline(cr, uid, user_input, context=context)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # First page
            errpage = self._check_disposable(cr, uid, survey, user_input_obj, context=context)
            if errpage:
                return errpage

            page, page_nr, last = survey_obj.next_page(cr, uid, user_input, 0, go_back=False, context=context)
            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('survey.survey', data)
        elif user_input.state == 'done':  # Display success message
            return request.website.render('survey.sfinished', {'survey': survey,
                                                               'token': token,
                                                               'user_input': user_input})
        elif user_input.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = survey_obj.next_page(cr, uid, user_input, user_input.last_displayed_page_id.id, go_back=flag, context=context)

            #special case if you click "previous" from the last page, then leave the survey, then reopen it from the URL, avoid crash
            if not page:
                page, page_nr, last = survey_obj.next_page(cr, uid, user_input, user_input.last_displayed_page_id.id, go_back=True, context=context)

            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('survey.survey', data)
        else:
            return request.website.render("website.403")
