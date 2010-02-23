from __future__ import absolute_import

import httplib
import logging

from django.db.models import Count
from djview import *
from djview.jsonutil import dump, dumps

from .forms import forms_for_survey
from .models import Survey, Submission, Answer


def _user_entered_survey(request, survey):
    return bool(survey.submissions_for(request.user, request.session.session_key.lower()).count())


def _user_too_many_entries(request, survey):
    return all((
        not survey.allow_multiple_submissions,
        _user_entered_survey(request, survey),))

def _get_remote_ip(request):
    forwarded=request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META['REMOTE_ADDR']


def login_url(request):
    return reverse("auth_login") + '?next=%s' % request.path


def _survey_submit(request, survey):
    if survey.require_login and request.user.is_anonymous():
        # again, the form should only be shown after the user is logged in, but
        # to be safe...
        return HttpResponseRedirect(login_url(request))
    if not hasattr(request, 'session'):
        return HttpResponse("Cookies must be enabled to use this application.", status=httplib.FORBIDDEN)
    if (_user_too_many_entries(request, survey)):
        return render_with_request(['crowdsourcing/%s_already_submitted.html' % survey.slug,
                                    'crowdsourcing/already_submitted.html'],
                                   dict(survey=survey),
                                   request)

    forms = forms_for_survey(survey, request)
    
    if all(form.is_valid() for form in forms):
        submission_form = forms[0]
        submission = submission_form.save(commit=False)
        submission.survey = survey
        submission.ip_address = _get_remote_ip(request)
        submission.is_public = not survey.moderate_submissions
        if request.user.is_authenticated():
            submission.user = request.user
        submission.save()
        for form in forms[1:]:
            answer = form.save(commit=False)
            if isinstance(answer, (list,tuple)):
                for a in answer:
                    a.submission=submission
                    a.save()
            else:
                print form, answer
                if answer:
                    answer.submission=submission
                    answer.save()
        # go to survey results/thanks page
        if survey.can_have_public_submissions():
            return _survey_results_redirect(request, survey, thanks=True)
        return _survey_show_form(request, survey, ())
    else:
        return _survey_show_form(request, survey, forms)


def _survey_show_form(request, survey, forms):
    specific_template = 'crowdsourcing/%s_survey_detail.html' % survey.slug
    entered = _user_entered_survey(request, survey)
    return render_with_request([specific_template,
                                'crowdsourcing/survey_detail.html'],
                               dict(survey=survey,
                                    forms=forms,
                                    entered=entered,
                                    login_url=login_url(request)),
                               request)


def can_show_form(request, survey):
    authenticated = request.user.is_authenticated()
    return all((
        survey.is_open,
        authenticated or not survey.require_login,
        not _user_too_many_entries(request, survey)))
    
def survey_detail(request, slug):
    survey = get_object_or_404(Survey, slug=slug, is_published=True)
    if not survey.is_open and survey.can_have_public_submissions():
        return _survey_results_redirect(request, survey)
    need_login = all((
        survey.is_open,
        survey.require_login,
        not request.user.is_authenticated()))
    if can_show_form(request, survey):
        if request.method == 'POST':
            return _survey_submit(request, survey)
        forms = forms_for_survey(survey, request)
    elif need_login:
        forms = ()
    elif survey.can_have_public_submissions():
        return _survey_results_redirect(request, survey)
    else: # Survey is closed with private results.
        forms = ()
    return _survey_show_form(request, survey, forms)


def survey_results(request, slug, page=None):
    """
    This should use some logic to show the most likely-to-be-relevant
    results -- and also consider the archive policy.
    """
    if page is None:
        page = 1
    else:
        page = get_int_or_404(page)

    survey = get_object_or_404(Survey.live, slug=slug)
    if not survey.can_have_public_submissions():
        raise Http404
    submissions = survey.public_submissions()
    paginator, page_obj = paginate_or_404(submissions, page)
    # clean this out?
    thanks = request.session.get('survey_thanks_%s' % survey.slug)
    return render_with_request(['crowdsourcing/%s_survey_results.html' % survey.slug,
                                'crowdsourcing/survey_results.html'],
                               dict(survey=survey,
                                    thanks=thanks,
                                    paginator=paginator,
                                    page_obj=page_obj),
                               request)
    

def _survey_results_redirect(request, survey, thanks=False):
    url = reverse('survey_results', kwargs={'slug': survey.slug})
    response = HttpResponseRedirect(url)
    if thanks:
        request.session['survey_thanks_%s' % survey.slug] = '1'
    return response


def can_enter(request, slug):
    survey = get_object_or_404(Survey.live, slug=slug)
    response = HttpResponse(mimetype='application/json')
    dump(not _user_too_many_entries(request, survey), response)
    return response


def allowed_actions(request, slug):
    survey = get_object_or_404(Survey.live, slug=slug)
    response = HttpResponse(mimetype='application/json')
    dump({"enter": can_show_form(request, survey),
          "view": survey.can_have_public_submissions()}, response)
    return response


def _survey_questions_api(survey, questionData):
    response=HttpResponse(mimetype='application/json')
    dump({"id": survey.id, "title": survey.title, "tease": survey.tease, "description": survey.description, "questions": questionData}, response)
    return response
    
def questions(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    questionData = {}
    for q in survey.questions.all():
        questionData[q.id] = {"question": q.question, "answers": q.parsed_options}
    return _survey_questions_api(survey, questionData)

def aggregate_results(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    questionData = {}
    for question in survey.questions.all():
        subData = {}
        for answer in question.answer_set.values('text_answer').annotate(count=Count("id")):
            subData[answer['text_answer']] = answer['count']
        questionData[question.question] = subData
    return _survey_questions_api(survey, questionData)

def survey_results_json(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    qs=survey.public_submissions()

    vars=dict((k.encode('utf-8', 'ignore'), v) for k, v in (request.POST if request.method=='POST' else request.GET).items())
    limit=vars.pop('limit', 30)
    offset=vars.pop('offset', 0)
    order=vars.pop('order', None)
    cntonly=vars.pop('countonly', False)
    callback=vars.pop('callback', None)
    if vars:
        qs=qs.filter(**vars)
    cnt=qs.count()
    if cntonly:
        data=dict(count=cnt,
                  survey=survey.to_jsondata())
    else:
        if order:
            qs=qs.order_by(order)
        res=qs[offset:limit]
        data=dict(results=[x.to_jsondata() for x in res],
                  survey=survey.to_jsondata(),
                  count=cnt)

    if callback:
        body='<script type="text/javascript">%s(%s);</script>' % (callback,
                                                                  dumps(data))
        return HttpResponse(body, mimetype='application/javascript')        
    else:
        response=HttpResponse(mimetype='application/json')
        dump(data, response)
    return response
    


def survey_results_grid(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    submissions=survey.public_submissions()
    # this might call the JSON view, or not.
    return render_with_request(['crowdsourcing/%s_survey_grid.html' % survey.slug,
                                'crowdsourcing/survey_grid.html'],
                               dict(survey=survey,
                                    submissions=submissions),
                               request)


def survey_results_map(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    location_fields=list(survey.get_public_location_fields())
    if not location_fields:
        raise Http404
    submissions=survey.public_submissions()    
    return render_with_request(['crowdsourcing/%s_survey_results_map.html' % survey.slug,
                                'crowdsourcing/survey_results_map.html'],
                               dict(survey=survey,
                                    submissions=submissions,
                                    location_fields=location_fields),
                               request)
    

def survey_results_archive(request, slug, page=None):    
    page=1 if page is None else get_int_or_404(page) 
    survey=get_object_or_404(Survey.live, slug=slug)
    archive_fields=list(survey.get_public_archive_fields())
    if not archive_fields:
        raise Http404
    submissions=survey.public_submissions()
    paginator, page_obj=paginate_or_404(submissions, page)
    return render_with_request(['crowdsourcing/%s_survey_results_archive.html' % survey.slug,
                                'crowdsourcing/survey_results_archive.html'],
                               dict(survey=survey,
                                    archive_fields=archive_fields,
                                    paginator=paginator,
                                    page_obj=page_obj),
                               request)
    

    
def survey_results_aggregate(request, slug):
    """
    this is where we generate graphs and all that good stuff.
    """
    survey=get_object_or_404(Survey.live, slug=slug)
    aggregate_fields=list(survey.get_public_aggregate_fields())
    if not aggregate_fields:
        raise Http404
    submissions=survey.public_submissions()
    return render_with_request(['crowdsourcing/%s_survey_results_aggregate.html' % survey.slug,
                                'crowdsourcing/survey_results_aggregate.html'],
                               dict(survey=survey,
                                    aggregate_fields=aggregate_fields,
                                    submissions=submissions),
                               request)
    
