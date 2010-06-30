from __future__ import absolute_import

import csv
from datetime import datetime
import httplib
from itertools import count
import logging
import smtplib

from django.conf import settings
from django.core.exceptions import FieldError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext as _rc
from django.utils.html import escape

from .forms import forms_for_survey
from .models import (
    Answer,
    OPTION_TYPE_CHOICES,
    Question,
    SURVEY_DISPLAY_TYPE_CHOICES,
    Submission,
    Survey,
    SurveyReport,
    SurveyReportDisplay,
    extra_from_filters,
    get_all_answers,
    get_filters)
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
    try:
        edit_url = reverse("admin:%s_%s_change" % view_args, args=(obj.id,))
    except NoReverseMatch:
        # Probably 'admin' is not a registered namespace on a site without an
        # admin. Just fake it.
        edit_url = "/admin/%s/%s/%d/" % (view_args + (obj.id,))
    admin_url = local_settings.SURVEY_ADMIN_SITE
    if not admin_url:
        admin_url = "http://" + request.META["HTTP_HOST"]
    elif len(admin_url) < 4 or admin_url[:4].lower() != "http":
        admin_url = "http://" + admin_url
    return admin_url + edit_url


def _send_survey_email(request, survey, submission):
    subject = survey.title
    sender = local_settings.SURVEY_EMAIL_FROM
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
    recipients = [a.strip() for a in survey.email.split(",")]
    email_msg = EmailMultiAlternatives(subject,
                                       html_email,
                                       sender,
                                       recipients)
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


FORMAT_CHOICES = ('json', 'csv', 'xml', 'http',)


def submissions(request, format):
    """ Use this view to make arbitrary queries on submissions. If the user is
    a logged in staff member, ignore submission.is_public,
    question.answer_is_public, and survey.can_have_public_submissions. Use the
    query string to pass keys and values. For example,
    /crowdsourcing/submissions/?survey=my-survey will return all submissions
    for the survey with slug my-survey.
    survey - the slug for the survey
    user - the username of the submittor. Leave blank for submissions without
        a logged in user.
    submitted_from and submitted_to - strings in the format YYYY-mm-ddThh:mm:ss
        For example, 2010-04-05T13:02:03
    featured - A blank value, 'f', 'false', 0, 'n', and 'no' all mean ignore
        the featured flag. Everything else means display only featured.
    You can also use filters in the survey report sense. Rather than document
    exactly what parameters you would pass, follow these steps to figure it
    out:
    1. Enable filters on your survey and the questions you want to filter on.
    2. Go to the report page and fill out the filters you want.
    3. Click Submit. 
    4. Examine the query string of the page you end up on and note which
        parameters are filled out. Use those same parameters here. """
    format = format.lower()
    if format not in FORMAT_CHOICES:
        msg = ("%s is an unrecognized format. Crowdsourcing recognizes "
               "these: %s") % (format, ", ".join(FORMAT_CHOICES))
        return HttpResponse(msg)
    is_staff = request.user.is_authenticated() and request.user.is_staff
    if is_staff:
        results = Submission.objects.all()
    else:
        # survey.can_have_public_submissions is complicated enough that
        # we'll check it in Python, not the database.
        results = Submission.objects.filter(is_public=True)
    results = results.select_related("survey", "user")
    basic_filters = (
        'survey',
        'user',
        'submitted_from',
        'submitted_to',
        'featured')
    get = request.GET.copy()
    keys = get.keys()
    survey_slug = ""
    for field in [f for f in keys if f in basic_filters]:
        value = get[field]
        if 'survey' == field:
            search_field = 'survey__slug'
            survey_slug = value
        elif 'user' == field:
            if '' == value:
                search_field = 'user'
                value = None
            else:
                search_field = 'user__username'
        elif field in ('submitted_from', 'submitted_to'):
            format = "%Y-%m-%dT%H:%M:%S"
            try:
                value = datetime.strptime(value, format)
            except ValueError:
                return HttpResponse(
                    ("Invalid %s format. Try, for example, "
                     "%s") % (field, datetime.now().strftime(format),))
            if 'submitted_from' == field:
                search_field = 'submitted_at__gte'
            else:
                search_field = 'submitted_at__lte'
        elif 'featured' == field:
            falses = ('f', 'false', 'no', 'n', '0',)
            value = len(value) and not value.lower() in falses
        # search_field is unicode but needs to be ascii.
        results = results.filter(**{str(search_field): value})
        get.pop(field)
    if get:
        if survey_slug:
            results = extra_from_filters(
                results,
                "crowdsourcing_submission.id",
                Survey.objects.get(slug=survey_slug),
                get)
        else:
            message = (
                "You've got a couple of extra filters here, and we "
                "aren't sure what to do with them. You may have just "
                "misspelled one of the basic filters (%s). You may have a "
                "filter from a particular survey in mind. In that case, just "
                "include survey=my-survey-slug in the query string. You may "
                "also be trying to pull some hotshot move like, \"Get me all "
                "submissions that belong to a survey with a filter named '%s' "
                "that match '%s'.\" Crowdsourcing could support this, but it "
                "would be pretty inneficient and, we're guessing, pretty "
                "rare. If that's what you're trying to do I'm afraid you'll "
                "have to do something more complicated like iterating through "
                "all your surveys.")
            item = get.items()[0]
            message = message % (", ".join(basic_filters), item[0], item[1])
            return HttpResponse(message)
    if not is_staff:
        rs = [r for r in results if r.survey.can_have_public_submissions()]
        results = rs
    answer_lookup = get_all_answers(results)
    result_data = [result.to_jsondata(answer_lookup) for result in results]

    for data in result_data:
        data.update(data["data"])
        data.pop("data")

    def get_keys():
        key_lookup = {}
        for data in result_data:
            for key in data.keys():
                key_lookup[key] = True
        return sorted(key_lookup.keys())

    if format == 'json':
        response = HttpResponse(mimetype='application/json')
        dump(result_data, response)
    elif format == 'csv':
        response = HttpResponse(mimetype='text/csv')
        keys = get_keys()
        writer.writerow(keys)
        for data in result_data:
            writer.writerow([data.get(key, "") for key in keys])
    elif format == 'xml':
        data_list = []
        for data in result_data:
            values = ["<%s>%s</%s>" % (k, str(v), k) for k, v in data.items()]
            data_list.append("<submission>%s</submission>" % "".join(values))
        subs = "<submissions>%s</submissions>" % "\n".join(data_list)
        response = HttpResponse(subs, mimetype='text/xml')
    elif format == 'http': # mostly for debugging.
        data_list = []
        keys = get_keys()
        results = [
            "<html><body><table>",
            "<tr>%s</tr>" % "".join(["<th>%s</th>" % k for k in keys])]
        for data in result_data:
            cells = ["<td>%s</td>" % data.get(key, "") for key in keys]
            results.append("<tr>%s</tr>" % "".join(cells))
        results.append("</table></body></html>")
        response = HttpResponse("\n".join(results))
    return response


def submission(request, id):
    template = 'crowdsourcing/submission.html'
    sub = get_object_or_404(Submission.objects, is_public=True, pk=id)
    return render_to_response(template, dict(submission=sub), _rc(request))


def _default_report(survey):
    field_count = count(1)
    OTC = OPTION_TYPE_CHOICES
    pie_choices = (
        OTC.BOOL,
        OTC.SELECT,
        OTC.CHOICE,
        OTC.NUMERIC_SELECT,
        OTC.NUMERIC_CHOICE)
    all_choices = pie_choices + (OTC.LOCATION, OTC.PHOTO)
    public_fields = survey.get_public_fields()
    fields = [f for f in public_fields if f.option_type in all_choices]
    report = SurveyReport(
        survey=survey,
        title=survey.title,
        summary=survey.description or survey.tease)
    displays = []
    for field in fields:
        if field.option_type in pie_choices:
            type = SURVEY_DISPLAY_TYPE_CHOICES.PIE
        elif field.option_type == OTC.LOCATION:
            type = SURVEY_DISPLAY_TYPE_CHOICES.MAP
        elif field.option_type == OTC.PHOTO:
            type = SURVEY_DISPLAY_TYPE_CHOICES.SLIDESHOW
        displays.append(SurveyReportDisplay(
            report=report,
            display_type=type,
            fieldnames=field.fieldname,
            annotation=field.label,
            order=field_count.next()))
    report.survey_report_displays = displays
    return report


def survey_report(request, slug, report='', page=None):
    templates = ['crowdsourcing/survey_report_%s.html' % slug,
                 'crowdsourcing/survey_report.html']
    return _survey_report(request, slug, report, page, templates)


def embeded_survey_report(request, slug, report=''):
    templates = ['crowdsourcing/embeded_survey_report_%s.html' % slug,
                 'crowdsourcing/embeded_survey_report.html']
    return _survey_report(request, slug, report, None, templates)


def _survey_report(request, slug, report, page, templates):
    """ Show a report for the survey. As rating is done in a separate
    application we don't directly check request.GET["sort"] here.
    local_settings.PRE_REPORT is the place for that. """
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
    reports = survey.surveyreport_set.all()
    if report:
        report_obj = get_object_or_404(reports, slug=report)
    elif survey.default_report:
        args = {"slug": survey.slug, "report": survey.default_report.slug}
        return HttpResponseRedirect(reverse("survey_report_page_1",
                                    kwargs=args))
    else:
        report_obj = _default_report(survey)

    archive_fields = list(survey.get_public_archive_fields())
    fields = list(survey.get_public_fields())
    filters = get_filters(survey, request.GET)

    public = survey.public_submissions()
    id_field = "crowdsourcing_submission.id"
    submissions = extra_from_filters(public, id_field, survey, request.GET)
    # If you want to sort based on rating, wire it up here.
    if local_settings.PRE_REPORT:
        pre_report = get_function(local_settings.PRE_REPORT)
        submissions = pre_report(
            submissions=submissions,
            report=report_obj,
            request=request)

    ids = None
    if report_obj.limit_results_to:
        submissions = submissions[:report_obj.limit_results_to]
        ids = ",".join([str(s.pk) for s in submissions])
    if not report_obj.display_individual_results:
        submissions = submissions.none()
    paginator, page_obj = paginate_or_404(submissions, page)

    page_answers = get_all_answers(page_obj.object_list)

    pages_to_link = []
    for i in range(page - 5, page + 5):
        if 1 <= i <= paginator.num_pages:
            pages_to_link.append(i)
    if pages_to_link[0] > 1:
        pages_to_link = [1, False] + pages_to_link
    if pages_to_link[-1] < paginator.num_pages:
        pages_to_link = pages_to_link + [False, paginator.num_pages]

    context = dict(
        survey=survey,
        submissions=submissions,
        paginator=paginator,
        page_obj=page_obj,
        ids=ids,
        pages_to_link=pages_to_link,
        fields=fields,
        archive_fields=archive_fields,
        filters=filters,
        report=report_obj,
        page_answers=page_answers,
        request=request)

    return render_to_response(templates, context, _rc(request))


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


def location_question_results(
    request,
    question_id,
    submission_ids=None,
    limit_map_answers=None):
    question = get_object_or_404(Question.objects.select_related("survey"),
                                 pk=question_id,
                                 answer_is_public=True)
    if not question.survey.can_have_public_submissions():
        raise Http404
    icon_lookup = {}
    icon_questions = question.survey.icon_questions()
    for icon_question in icon_questions:
        icon_by_answer = {}
        for (option, icon) in icon_question.parsed_option_icon_pairs():
            if icon:
                icon_by_answer[option] = icon
        for answer in icon_question.answer_set.all():
            if answer.value in icon_by_answer:
                icon = icon_by_answer[answer.value]
                icon_lookup[answer.submission_id] = icon

    answers = question.answer_set.filter(
        ~Q(latitude=None),
        ~Q(longitude=None),
        submission__is_public=True)
    answers = extra_from_filters(
        answers,
        "submission_id",
        question.survey,
        request.GET)
    if submission_ids:
        answers = answers.filter(submission__in=submission_ids.split(","))
    if limit_map_answers:
        answers = answers[:limit_map_answers]
    entries = []
    view = "crowdsourcing.views.submission_for_map"
    for answer in answers:
        kwargs = {"id": answer.submission_id}
        d = {
            "lat": answer.latitude,
            "lng": answer.longitude,
            "url": reverse(view, kwargs=kwargs)}
        if answer.submission_id in icon_lookup:
            d["icon"] = icon_lookup[answer.submission_id]
        entries.append(d)
    response = HttpResponse(mimetype='application/json')
    dump({"entries": entries}, response)
    return response


def submission_for_map(request, id):
    template = 'crowdsourcing/submission_for_map.html'
    sub = get_object_or_404(Submission.objects, is_public=True, pk=id)
    return render_to_response(template, dict(submission=sub), _rc(request))
