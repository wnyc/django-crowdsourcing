from __future__ import absolute_import

import httplib
import logging

# django-viewutil
from djview import *

from .forms import forms_for_survey
from .models import Survey, Submission, Answer


def _survey_submit(request, survey):
    if survey.require_login and request.user.is_anonymous():
        # again, the form should only be shown after the user is logged in, but to be safe...
        return HttpResponseRedirect(reverse("auth_login") + '?next=%s' % request.path)
    if not hasattr(request, 'session'):
        return HttpResponse("Cookies must be enabled to use this application.", status=httplib.FORBIDDEN)
    if (not survey.allow_multiple_submissions and
        survey.submissions_for(request.user, request.session.session_key.lower()).count()):
        return render_with_request(['crowdsourcing/%s_already_submitted.html' % survey.slug,
                                    'crowdsourcing/already_submitted.html'],
                                   dict(survey=survey),
                                   request)

    forms=forms_for_survey(survey, request)
    
    if all(form.is_valid() for form in forms):
        submission_form=forms[0]
        submission=submission_form.save(commit=False)
        submission.survey=survey
        submission.ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META['REMOTE_ADDR'])
        submission.is_public=not survey.moderate_submissions
        submission.save()
        for form in forms:
            answer=form.save(commit=False)
            if isinstance(answer, (list,tuple)):
                for a in answer:
                    a.submission=submission
                    a.save()
            else:
                answer.submission=submission
                answer.save()
        # go to survey results/thanks page
        return _survey_results_redirect(request, survey, thanks=True)
    else:
        return _survey_show_form(request, survey, forms)


def _survey_show_form(request, survey, forms):
    return render_with_request(['crowdsourcing/%s_survey_detail.html' % survey.slug,
                                'crowdsourcing/survey_detail.html'],
                               dict(survey=survey, forms=forms),
                               request)


def survey_detail(request, slug):
    survey=get_object_or_404(Survey.live, slug=slug)
    can_show_form=survey.is_open and (request.user.is_authenticated() or not survey.require_login)
    
    if can_show_form:
        if request.method=='POST':
            return _survey_submit(request, survey)
        forms =forms_for_survey(survey, request)
    else:
        forms=()
    return _survey_show_form(request, survey, forms)


def survey_results(request, slug, page=None):
    if page is None:
        page=1
    else:
        page=get_int_or_404(page)

    survey=get_object_or_404(Survey.live, slug=slug)
    submissions=survey.public_submissions()
    paginator, page_obj=paginate_or_404(submissions, page)
    # clean this out?
    thanks=request.session.get('survey_thanks_%s' % slug)
    return render_with_request(['crowdsourcing/%s_survey_results.html' % slug,
                                'crowdsourcing/survey_results.html'],
                               dict(survey=survey,
                                    thanks=thanks,
                                    paginator=paginator,
                                    page_obj=page_obj),
                               request)
    

def _survey_results_redirect(request, survey, thanks=False):
    url=reverse('survey_results', kwargs={'slug': survey.slug})
    response=HttpResponseRedirect(url)
    if thanks:
        request.session['survey_thanks_%s' % survey.slug]='1'
    return response
