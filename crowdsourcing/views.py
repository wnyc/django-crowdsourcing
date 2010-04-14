from __future__ import absolute_import

from datetime import datetime
import httplib
from itertools import count
import logging

from django.conf import settings
from django.core.exceptions import FieldError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext as _rc
from django.utils.html import escape

from .forms import forms_for_survey
from .models import (Survey, Submission, Answer, SurveyReportDisplay,
                     SURVEY_DISPLAY_TYPE_CHOICES, SurveyReport,
                     extra_from_filters, OPTION_TYPE_CHOICES, get_filters)
from .jsonutils import dump, dumps

from .util import ChoiceEnum, get_function
from . import settings as local_settings


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


def _login_url(request):
    if local_settings.LOGIN_VIEW:
        return reverse(local_settings.LOGIN_VIEW) + '?next=%s' % request.path
    return "/?login_required=true"


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
        slug_template = 'crowdsourcing/%s_already_submitted.html' % survey.slug
        return render_to_response([slug_template,
                                   'crowdsourcing/already_submitted.html'],
                                  dict(survey=survey),
                                  _rc(request))

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
        if survey.email:
            _send_survey_email(request, survey, submission)
        if survey.can_have_public_submissions():
            return _survey_results_redirect(request, survey, thanks=True)
        return _survey_show_form(request, survey, ())
    else:
        return _survey_show_form(request, survey, forms)


def _url_for_edit(request, obj):
    view_args = (obj._meta.app_label, obj._meta.module_name,)
    edit_url = reverse("admin:%s_%s_change" % view_args,
                       args=(obj.id,))
    admin_url = local_settings.SURVEY_ADMIN_SITE
    if not admin_url:
        admin_url = "http://" + request.META["HTTP_HOST"]
    elif len(admin_url) < 4 or admin_url[:4].lower() != "http":
        admin_url = "http://" + admin_url
    return admin_url + edit_url


def _send_survey_email(request, survey, submission):
    subject = survey.title
    sender = local_settings.SURVEY_EMAIL_FROM
    recipient = survey.email
    links = [(_url_for_edit(request, submission), "Edit Submission"),
             (_url_for_edit(request, survey), "Edit Survey"),]
    if survey.can_have_public_submissions():
        u = "http://" + request.META["HTTP_HOST"] + _survey_report_url(survey)
        links.append((u, "View Survey",))
    parts = ["<a href=\"%s\">%s</a>" % link for link in links]
    set = submission.answer_set.all()
    lines = ["%s: %s" % (a.question.label, escape(a.value),) for a in set]
    parts.extend(lines)
    html_email = "<br/>\n".join(parts)
    email_msg = EmailMultiAlternatives(subject,
                                       html_email,
                                       sender,
                                       [recipient])
    email_msg.attach_alternative(html_email, 'text/html')
    try:
        email_msg.send()
    except smtplib.SMTPException as ex:
        logging.exception("SMTP error sending email: %s" % str(ex))
    except Exception as ex:
        logging.exception("Unexpected error sending email: %s" % str(ex))


def _survey_show_form(request, survey, forms):
    specific_template = 'crowdsourcing/%s_survey_detail.html' % survey.slug
    entered = _user_entered_survey(request, survey)
    return render_to_response([specific_template,
                               'crowdsourcing/survey_detail.html'],
                              dict(survey=survey,
                                   forms=forms,
                                   entered=entered,
                                   login_url=_login_url(request)),
                              _rc(request))


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
    response = HttpResponseRedirect(_survey_report_url(survey))
    if thanks:
        request.session['survey_thanks_%s' % survey.slug] = '1'
    return response


def _survey_report_url(survey):
    return reverse('survey_default_report_page_1',
                   kwargs={'slug': survey.slug})


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


def submissions(request):
    """ Use this view to make arbitrary queries on submissions. Use the query
    string to pass keys and values. For example,
    /crowdsourcing/submissions/?survey=my-survey will return all submissions
    for the survey with slug my-survey.
    survey - the slug for the survey
    user - the username of the submittor. Leave blank for submissions without
        a logged in user.
    submitted_from and submitted_to - strings in the format YYYY-mm-ddThh:mm:ss
        For example, 2010-04-05T13:02:03
    featured - A blank value, 'f', 'false', 0, 'n', and 'no' all mean not
        featured. Everything else means featured. """
    response = HttpResponse(mimetype='application/json')
    results = Submission.objects.filter(is_public=True)
    valid_filters = (
        'survey',
        'user',
        'submitted_from',
        'submitted_to',
        'featured')
    for field in request.GET.keys():
        if field in valid_filters:
            value = request.GET[field]
            if 'survey' == field:
                field = 'survey__slug'
            elif 'user' == field:
                if '' == value:
                    field = 'user'
                    value = None
                else:
                    field = 'user__username'
            elif field in ('submitted_from', 'submitted_to'):
                format = "%Y-%m-%dT%H:%M:%S"
                try:
                    value = datetime.strptime(value, format)
                except ValueError:
                    return HttpResponse(
                        ("Invalid %s format. Try, for example, "
                         "%s") % (field, datetime.now().strftime(format),))
                if 'submitted_from' == field:
                    field = 'submitted_at__gte'
                else:
                    field = 'submitted_at__lte'
            elif 'featured' == field:
                falses = ('f', 'false', 'no', 'n', '0',)
                value = len(value) and not value.lower() in falses
            # field is unicode but needs to be ascii.
            results = results.filter(**{str(field): value})
        else:
            return HttpResponse(("You can't filter on %s. Valid options are "
                                 "%s.") % (field, valid_filters))
    dump([result.to_jsondata() for result in results], response)
    return response


def _default_report(survey):
    field_count = count(1)
    fields = survey.get_public_fields().filter(option_type__in=(
        OPTION_TYPE_CHOICES.BOOLEAN,
        OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE,
        OPTION_TYPE_CHOICES.RADIO_LIST))
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


def survey_report(request, slug, report='', page=None):
    """ Show a report for the survey. """
    if page is None:
        page = 1
    else:
        try:
            page = int(page)
        except ValueError:
            raise Http404
    survey = _get_survey_or_404(slug)
    # is the survey anything we can actually have a report on?
    if not survey.can_have_public_submissions():
        raise Http404

    location_fields = list(survey.get_public_location_fields())
    archive_fields = list(survey.get_public_archive_fields())
    aggregate_fields = list(survey.get_public_aggregate_fields())
    fields = list(survey.get_public_fields())
    filters = get_filters(survey, request.GET)

    public = survey.public_submissions()
    id_field = "crowdsourcing_submission.id"
    submissions = extra_from_filters(public, id_field, survey, request.GET)
    if local_settings.PRE_REPORT:
        pre_report = get_function(local_settings.PRE_REPORT)
        submissions = pre_report(submissions, request)

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

    return render_to_response(templates,
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
                                   reports=reports,
                                   report=the_report,
                                   request=request),
                              _rc(request))


def paginate_or_404(queryset, page, num_per_page=20):
    """
    paginate a queryset (or other iterator) for the given page, returning the
    paginator and page object. Raises a 404 for an invalid page.
    """
    if page is None:
        page = 1
    paginator = Paginator(queryset, num_per_page)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    except InvalidPage:
        raise Http404
    return paginator, page_obj
