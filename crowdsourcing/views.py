from __future__ import absolute_import

import httplib
from itertools import count
import logging

from django.conf import settings
from djview import *
from djview.jsonutil import dump, dumps

from .forms import forms_for_survey
from .models import (Survey, Submission, Answer, SurveyReportDisplay,
                     SURVEY_DISPLAY_TYPE_CHOICES, SurveyReport)


def _user_entered_survey(request, survey):
    return bool(survey.submissions_for(
        request.user,
        request.session.session_key.lower()).count())


def _entered_no_more_allowed(request, survey):
    """ The user entered the survey and the survey allows only one entry. """
    return all((
        not survey.allow_multiple_submissions,
        _user_entered_survey(request, survey),))


def _get_remote_ip(request):
    forwarded=request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META['REMOTE_ADDR']


def get_filters(requestdata, survey):
    data_filters = []
    for field in survey.get_filters():
        value = requestdata.get(field.fieldname)
        if value:
            data_filters.append((field, value,))
    return data_filters


def _filter_submissions(survey, data_filters):
    """ Based on the query string, limit the survey results displayed
    both in agregate and listed format. """
    submissions = survey.public_submissions()
    if data_filters:
        for field, value in data_filters:
            where = (
                "crowdsourcing_submission.id in (SELECT submission_id FROM "
                "crowdsourcing_answer WHERE text_answer = %%s AND "
                "question_id = %d)") % field.id
            kwargs = dict(where=[where], params=[value])
            submissions = submissions.extra(**kwargs)
    return submissions


def _login_url(request):
    return reverse("auth_login") + '?next=%s' % request.path


def _get_survey_or_404(slug):
    return get_object_or_404(Survey.live, slug=slug)


def _survey_submit(request, survey):
    if survey.require_login and request.user.is_anonymous():
        # again, the form should only be shown after the user is logged in, but
        # to be safe...
        return HttpResponseRedirect(_login_url(request))
    if not hasattr(request, 'session'):
        return HttpResponse("Cookies must be enabled to use this application.",
                            status=httplib.FORBIDDEN)
    if (_entered_no_more_allowed(request, survey)):
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
            if isinstance(answer, (list, tuple)):
                for a in answer:
                    a.submission=submission
                    a.save()
            else:
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
                                    login_url=_login_url(request)),
                               request)


def _can_show_form(request, survey):
    authenticated = request.user.is_authenticated()
    return all((
        survey.is_open,
        authenticated or not survey.require_login,
        not _entered_no_more_allowed(request, survey)))


def survey_detail(request, slug):
    """ When you load the survey, this view decides what to do. It displays
    the form, redirects to the results page, displays messages, or whatever
    makes sense based on the survey, the user, and the user's entries. """
    survey = _get_survey_or_404(slug)
    if not survey.is_open and survey.can_have_public_submissions():
        return _survey_results_redirect(request, survey)
    need_login = (survey.is_open
                  and survey.require_login
                  and not request.user.is_authenticated())
    if _can_show_form(request, survey):
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


def _survey_results_redirect(request, survey, thanks=False):
    url = reverse('survey_default_report_page_1', kwargs={'slug': survey.slug})
    response = HttpResponseRedirect(url)
    if thanks:
        request.session['survey_thanks_%s' % survey.slug] = '1'
    return response


def allowed_actions(request, slug):
    survey = _get_survey_or_404(slug)
    response = HttpResponse(mimetype='application/json')
    dump({"enter": _can_show_form(request, survey),
          "view": survey.can_have_public_submissions()}, response)
    return response


def questions(request, slug):
    response = HttpResponse(mimetype='application/json')
    dump(_get_survey_or_404(slug).to_jsondata(), response)
    return response


def _default_report(survey):
    field_count = count(1)
    fields = survey.get_public_aggregate_fields()
    report = SurveyReport(
        survey=survey,
        title=survey.title,
        summary=survey.description or survey.tease)
    report.survey_report_displays = [SurveyReportDisplay(
        report=report,
        display_type=SURVEY_DISPLAY_TYPE_CHOICES.PIE,
        fieldnames=field.fieldname,
        annotation=field.label,
        order=field_count.next()) for field in fields]
    return report


class Filter:
    def __init__(self, field, request):
        self.key = field.fieldname
        self.label = field.label
        self.choices = field.parsed_options
        self.value = request.GET.get(self.key, "")


def survey_report(request, slug, report='', page=None):
    """ Show a report for the survey. """
    page = 1 if page is None else get_int_or_404(page)
    survey = _get_survey_or_404(slug)
    # is the survey anything we can actually have a report on?
    if not survey.can_have_public_submissions():
        raise Http404

    location_fields = list(survey.get_public_location_fields())
    archive_fields = list(survey.get_public_archive_fields())
    aggregate_fields = list(survey.get_public_aggregate_fields())
    fields = list(survey.get_public_fields())
    filters = [Filter(f, request) for f in aggregate_fields if f.is_filterable]

    data_filters = get_filters(request.GET, survey)
    submissions = _filter_submissions(survey, data_filters)
    paginator, page_obj = paginate_or_404(submissions, page)
    pages_to_link = []
    for i in range(page - 5, page + 5):
        if 1 <= i <= paginator.num_pages:
            pages_to_link.append(i)
    if pages_to_link[0] > 1:
        pages_to_link = [1, False] + pages_to_link
    if pages_to_link[-1] < paginator.num_pages:
        pages_to_link = pages_to_link + [False, paginator.num_pages]
    reports = survey.surveyreport_set.all()
    if report:
        the_report = get_object_or_404(reports, slug=report)
    elif reports:
        args = {"slug": survey.slug, "report": reports[0].slug}
        return HttpResponseRedirect(reverse("survey_report_page_1", args))
    else:
        the_report = _default_report(survey)
    templates = ['crowdsourcing/%s_survey_report.html' % survey.slug,
                 'crowdsourcing/survey_report.html']

    return render_with_request(templates,
                               dict(survey=survey,
                                    submissions=submissions,
                                    paginator=paginator,
                                    page_obj=page_obj,
                                    pages_to_link=pages_to_link,
                                    fields=fields,
                                    location_fields=location_fields,
                                    archive_fields=archive_fields,
                                    aggregate_fields=aggregate_fields,
                                    filters=filters,
                                    data_filters=data_filters,
                                    reports=reports,
                                    report=the_report),
                               request)
