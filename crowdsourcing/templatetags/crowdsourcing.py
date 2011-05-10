from __future__ import absolute_import
import logging
import re

from django import template
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.files.images import get_image_dimensions
from django.core.urlresolvers import reverse
from django.template import Node
from django.utils.safestring import mark_safe
from django.utils.html import escape, strip_tags
from sorl.thumbnail.base import ThumbnailException

from ..crowdsourcing.models import (
    extra_from_filters, AggregateResultCount, AggregateResultSum,
    AggregateResultAverage, AggregateResult2AxisCount, Answer, FILTER_TYPE,
    OPTION_TYPE_CHOICES, SURVEY_AGGREGATE_TYPE_CHOICES, get_all_answers)
from crowdsourcing.views import location_question_results
from crowdsourcing.util import ChoiceEnum, get_function
from crowdsourcing import settings as local_settings

if local_settings.OEMBED_EXPAND:
    try:
        oembed_expand = get_function(local_settings.OEMBED_EXPAND)
    except Exception as ex:
        args = (local_settings.OEMBED_EXPAND, str(ex))
        message = ("Got this exception while trying to get function %s. "
                   "settings.OEMBED_EXPAND should be in the format "
                   "path.to.module.function_name Will just display video "
                   "links for now. %s") % args
        logging.warn(message)
        oembed_expand = None
else:
    try:
        from ..crowdsourcing.oembedutils import oembed_expand
    except ImportError as ex:
        message = 'oembed not installed. Will just display links to videos. %s'
        logging.warn(message % str(ex))
        oembed_expand = None


""" We originally developed for Mako templates, but we also want to support
Django templates. We use simple tags which work both as tags and as functions
returning safe strings. """


register = template.Library()


def yahoo_api():
    return mark_safe("\n".join([
        '<script src="http://yui.yahooapis.com/2.8.1/build/yuiloader/yuiloader-min.js"></script>',
        '<style>',
        '  .chart_div { width: 600px; height: 300px; }',
        '</style>']))
register.simple_tag(yahoo_api)


def jquery_and_google_api():
    key = ""
    if local_settings.GOOGLE_MAPS_API_KEY:
        key = '?key=%s' % local_settings.GOOGLE_MAPS_API_KEY
    jsapi = "".join([
        '<script type="text/javascript" src="http://www.google.com/jsapi',
        key,
        '"></script>'])
    return mark_safe("\n".join([
        jsapi,
        '<script type="text/javascript">',
        '  google.load("jquery", "1.4");',
        '</script>']))
register.simple_tag(jquery_and_google_api)


def filter(wrapper_format, key, label, html):
    label_html = '<label for="%s">%s:</label> ' % (key, label,)
    return mark_safe(wrapper_format % (label_html + html))
register.simple_tag(filter)


def select_filter(wrapper_format, key, label, value, choices, blank=True):
    """ choices can contain either strings which will be used for both the
    value and the display, or (value, display) tuples. """
    html = ['<select id="%s" name="%s">' % (key, key,)]
    if blank:
        html.append('<option value="">---------</option>')
    for choice in choices:
        option_value = display = choice
        if hasattr(choice, "__iter__"):
            option_value, display = choice[0], choice[1]
        option_value, display = strip_tags(option_value), strip_tags(display)
        html.append('<option value="%s"' % option_value)
        if value == u"%s" % option_value:
            html.append('selected="selected"')
        html.append('>%s</option>' % display)
    html.append('</select>')
    return filter(wrapper_format, key, label, "\n".join(html))
register.simple_tag(select_filter)


def range_filter(wrapper_format, key, label, from_value, to_value):
    html = [
        '<span id="%s">' % key,
        '<label for="%s_from">From:</label>' % key,
        '<input type="text" id="%s_from"' % key,
        'name="%s_from" value="%s" />' % (key, escape(from_value)),
        '<label for="%s_to">To:</label>' % key,
        '<input type="text" id="%s_to"' % key,
        'name="%s_to" value="%s" />' % (key, escape(to_value)),
        '</span>']
    return filter(wrapper_format, key, label, "\n".join(html))
register.simple_tag(range_filter)


def distance_filter(wrapper_format, key, label, within_value, location_value):
    html = [
        '<span id="%s">' % key,
        '<label for="%s_within">Within</label> ' % key,
        '<input type="text" id="%s_within"' % key,
        'name="%s_within" value="%s" /> ' % (key, escape(within_value)),
        '<label for="%s_location">miles of</label> ' % key,
        '<input type="text" id="%s_location"' % key,
        'name="%s_location" value="%s" />' % (key, escape(location_value)),
        '</span>']
    return filter(wrapper_format, key, label, "\n".join(html))
register.simple_tag(distance_filter)


def filter_as_li(filter):
    output = []
    wrapper_format = "<li>%s</li>"
    if FILTER_TYPE.CHOICE == filter.type:
        output.append(select_filter(wrapper_format,
                                    filter.key,
                                    filter.label,
                                    filter.value,
                                    filter.choices))
    elif FILTER_TYPE.RANGE == filter.type:
        output.append(range_filter(wrapper_format,
                                   filter.key,
                                   filter.label,
                                   filter.from_value,
                                   filter.to_value))
    elif FILTER_TYPE.DISTANCE == filter.type:
        output.append(distance_filter(wrapper_format,
                                   filter.key,
                                   filter.label,
                                   filter.within_value,
                                   filter.location_value))
    return mark_safe("\n".join(output))
register.simple_tag(filter_as_li)


def filters_as_ul(filters):
    if not filters:
        return ""
    out = ['<form method="GET">',
           '<ul class="filters">']
    out.extend([filter_as_li(f) for f in filters])
    out.extend(['</ul>',
                '<input type="submit" value="Submit" />',
                '</form>'])
    return mark_safe("\n".join(out))
register.simple_tag(filters_as_ul)


def yahoo_pie_chart(display, question, request_get, is_staff=False):
    report = display.get_report()
    survey = report.survey
    aggregate = AggregateResultCount(survey,
                                     question,
                                     request_get,
                                     report,
                                     is_staff=is_staff)
    if not aggregate.answer_values:
        return ""
    fieldname = question.fieldname
    args = {
        "answer_string": aggregate.yahoo_answer_string,
        "option_setup": "",
        "chart_type": "PieChart",
        "response_schema": '{fields: ["%s", "count"]}' % fieldname,
        "options": "dataField: 'count', categoryField: '%s'" % fieldname,
        "style": """
            {padding: 20,
             legend: {display: "right",
                      padding: 10,
                      spacing: 5,
                      font: {family: "Arial",
                             size: 13
                            }
                     }
            }"""}
    id_args = (display.index_in_report(), question.id)
    return _yahoo_chart(display, "%d_%d" % id_args, args)
register.simple_tag(yahoo_pie_chart)


def yahoo_bar_chart(display, request_get, is_staff=False):
    return _yahoo_bar_line_chart_helper(display,
                                        request_get,
                                        "ColumnChart",
                                        is_staff=is_staff)
register.simple_tag(yahoo_bar_chart)


def yahoo_line_chart(display, request_get, is_staff=False):
    return _yahoo_bar_line_chart_helper(display,
                                        request_get,
                                        "LineChart",
                                        is_staff=is_staff)
register.simple_tag(yahoo_line_chart)


def _yahoo_bar_line_chart_helper(display,
                                 request_get,
                                 chart_type,
                                 is_staff=False):
    y_axes = display.questions()
    SATC = SURVEY_AGGREGATE_TYPE_CHOICES
    return_value = []
    if display.aggregate_type != SATC.COUNT and not y_axes:
        message = ("This chart uses y axes '%s', none of which are questions "
                   "in this survey.") % display.fieldnames
        return issue(message)
    x_axis = display.x_axis_question()
    if not x_axis:
        message = ("This chart uses x axis '%s' which isn't a question in "
                   "this survey.") % display.x_axis_fieldname
        return issue(message)
    single_count = False
    report = display.get_report()
    if display.aggregate_type in [SATC.DEFAULT, SATC.SUM]:
        aggregate_function = "Sum"
        aggregate = AggregateResultSum(y_axes, x_axis, request_get, report)
    elif display.aggregate_type == SATC.AVERAGE:
        aggregate_function = "Average"
        aggregate = AggregateResultAverage(y_axes, x_axis, request_get, report)
    elif display.aggregate_type == SATC.COUNT:
        aggregate_function = "Count"
        if y_axes:
            aggregate = AggregateResult2AxisCount(
                y_axes,
                x_axis,
                request_get,
                report)
        else:
            single_count = True
            survey = x_axis.survey
            aggregate = AggregateResultCount(
                survey,
                x_axis,
                request_get,
                report,
                is_staff=is_staff)
    if not aggregate.answer_values:
        return ""
    answer_string = aggregate.yahoo_answer_string
    series = []
    series_format = '{displayName: "%s", yField: "%s", style: {size: 10}}'
    if single_count:
        y_axis_label = "Count"
        fieldnames = ["count", x_axis.fieldname]
        series.append(series_format % ("Count", "count"))
    else:
        y_labels = ", ".join([y.label for y in y_axes])
        y_axis_label = "%s %s" % (aggregate_function, y_labels)
        axes = list(y_axes) + [x_axis]
        fieldnames = [f.fieldname for f in axes]
        for question in y_axes:
            series.append(series_format % (question.label, question.fieldname))
    option_setup_args = (
        "NumericAxis" if x_axis.is_numeric else "CategoryAxis",
        x_axis.label,
        y_axis_label,)
    option_setup_args = tuple(l.replace('"', r'\"') for l in option_setup_args)
    index = display.index_in_report()
    option_setup = """
        var xAxis = new YAHOO.widget.%s();
        xAxis.title = "%s";
        var yAxis = new YAHOO.widget.NumericAxis();
        yAxis.title = "%s";
        """ % option_setup_args
    options = {
        "series": "[%s]" % ",\n".join(series),
        "xField": '"%s"' % x_axis.fieldname,
        "xAxis": "xAxis",
        "yAxis": "yAxis"}
    options = ",\n".join(["%s: %s" % item for item in options.items()])
    fieldnames_str = ", ".join(['"%s"' % f for f in fieldnames])
    args = {
        "answer_string": answer_string,
        "option_setup": option_setup,
        "chart_type": chart_type,
        "response_schema": '{fields: [%s]}' % fieldnames_str,
        "style": '{xAxis: {labelRotation: -45}, yAxis: {titleRotation: -90}}',
        "options": options}
    return_value.append(_yahoo_chart(display, str(index), args))
    for question in y_axes:
        if not question.is_numeric:
            message = ("%s isn't numeric so it doesn't work as a y axis. "
                       "Update the fieldnames of this Survey Report Display.")
            message = message % question.fieldname
            return_value.append(issue(message))
    return mark_safe("\n".join(return_value))


def _yahoo_chart(display, unique_id, args):
    out = [
        '<h2 class="chart_title">%s</h2>' % display.annotation,
        '<div class="chart_div" id="chart%s">' % unique_id,
        'Unable to load Flash content. The YUI Charts Control ',
        'requires Flash Player 9.0.45 or higher. You can install the ',
        'latest version at the ',
        '<a href="http://www.adobe.com/go/getflashplayer">',
        'Adobe Flash Player Download Center</a>.',
        '</div>']
    args.update(
        data_var='data%s' % unique_id,
        div_id="chart%s" % unique_id)
    script = """
        <script type="text/javascript">
          yahooChartCallbacks.push(function() {
            YAHOO.widget.Chart.SWFURL =
              "http://yui.yahooapis.com/2.8.0r4/build/charts/assets/charts.swf";
            var answerData = %(answer_string)s;
            var %(data_var)s = new YAHOO.util.DataSource(answerData);
            %(data_var)s.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
            %(data_var)s.responseSchema = %(response_schema)s;
            %(option_setup)s
            var %(div_id)s = new YAHOO.widget.%(chart_type)s(
              "%(div_id)s",
              %(data_var)s,
              {%(options)s,
  
               style: %(style)s,
               expressInstall: "assets/expressinstall.swf"});
          });
        </script>""" % args
    out.append(script)
    return mark_safe("\n".join(out))


def google_map(display, question, report, is_popup=False):
    map_id = "map_%d" % display.order
    detail_id = "map_detail_%d" % question.id
    kwargs = {
        "question_id": question.pk,
        "limit_map_answers": display.limit_map_answers or 0}
    if report.slug:
        kwargs["survey_report_slug"] = report.slug
    data_url = reverse(location_question_results, kwargs=kwargs)
    img = '<img class="loading" src="/media/img/loading.gif" alt="loading" />'
    lat = number_to_javascript(display.map_center_latitude)
    lng = number_to_javascript(display.map_center_longitude)
    zoom = number_to_javascript(display.map_zoom)
    map_args = (map_id, detail_id, data_url, lat, lng, zoom)
    out = [
        '<div class="google_map_wrapper">']
    if not is_popup:
        out.append('  <h2 class="chart_title">%s</h2>' % display.annotation)
    out.extend([
        '  <div id="%s" class="google_map">' % map_id,
        '    ' + img,
        '  </div>',
        '  <div id="%s" class="map_story"></div>' % detail_id,
        '  <script type="text/javascript">',
        '    setupMap("%s", "%s", "%s", %s, %s, %s);' % map_args,
        '  </script>'])
    if not is_popup:
        kwargs = dict(
            question_id=question.pk,
            display_id=display.pk if display.pk else 0)
        if report.slug:
            kwargs["survey_report_slug"] = report.slug
        url = reverse('location_question_map', kwargs=kwargs)
        full_url = "http://%s%s" % (Site.objects.get_current().domain, url)
        out.extend([
            '  <ul class="map_tools">',
            '    <li><a href="%s" target="_blank">popout</a></li>' % url,
            '    <li><a href="#" class="map_embed_link">embed</a></li>',
            '  </ul>',
            '  <fieldset class="map_embed" style="display: none;">',
            '    <p>Copy and paste the HTML below to embed this map onto your web page.</p>',
            ('    <textarea id="audioplayer_125944_buttons_code" readonly="" rows="2" cols="44">'
            '&lt;iframe src="%s" height="320" width="500" &gt;&lt;/iframe&gt;</textarea>') % full_url,
            '    <a class="close-map-button" href="#">Close</a>',
            '  </fieldset>'])
    out.append('</div>')

    out.append(map_key(question.survey))
    return mark_safe("\n".join(out))
register.simple_tag(google_map)


def popup_google_map(display, question, report):
    return google_map(display, question, report, is_popup=True)
register.simple_tag(popup_google_map)


def simple_slideshow(display, question, request_GET, css):
    id = "slideshow_%d_%d" % (display.order, question.id)
    out = [
        '<h2 class="chart_title">%s</h2>' % display.annotation,
        '<ul class="%s" id="%s">' % (css, id),
        '<script type="text/javascript">',
        '$(function() {',
        "  $('#%s').jcarousel();" % id,
        '});',
        '</script>']
    caption_fieldnames = display.get_caption_fieldnames()
    caption_lookup = {}
    if caption_fieldnames:
        captions = Answer.objects.filter(
            question__fieldname__in=caption_fieldnames,
            question__survey=display.report.survey,
            submission__is_public=True)
        for caption in captions:
            if not caption.submission_id in caption_lookup:
                caption_lookup[caption.submission_id] = []
            append = "<div class='caption'>%s</div>" % str(caption.value)
            caption_lookup[caption.submission_id].append(append)
    answers = extra_from_filters(
        question.answer_set.all(),
        "submission_id",
        display.report.survey,
        request_GET)
    for answer in answers:
        try:
            image = answer.image_answer.thumbnail_tag
        except ThumbnailException:
            image = "Can't find %s" % answer.image_answer.url
        out.extend([
            '<li>',
            image,
            "\n".join(caption_lookup.get(answer.submission_id, [])),
            '</li>'])
    out.append("</ul>")
    return mark_safe("\n".join(out))
register.simple_tag(simple_slideshow)


def load_maps_and_charts():
    return mark_safe("\n".join([
        '<script type="text/javascript">',
        '  loadMapsAndCharts();',
        '</script>']))
register.simple_tag(load_maps_and_charts)


def submission_fields(submission,
                      fields=None,
                      page_answers=None,
                      request=None,
                      video_height=360,
                      video_width=288):
    is_staff = request and request.user.is_staff
    if not page_answers:
        page_answers = get_all_answers(
            [submission],
            include_private_questions=is_staff)
    if not fields:
        if is_staff:
            fields = list(submission.survey.get_fields())
        else:
            fields = list(submission.survey.get_public_fields())
    out = []
    answer_list = page_answers.get(submission.id, [])
    answers = {}
    when = submission.submitted_at.strftime("%B %d, %Y %I:%M:%S %p")
    out.append('<div class="date">%s</div>' % when)
    for answer in answer_list:
        answers[answer.question] = answer
    for question in fields:
        answer = answers.get(question, None)
        if answer and answer.value:
            out.append('<div class="field">')
            out.append('<label>%s</label>: ' % question.label)
            if answer.image_answer:
                valid = True
                try:
                    thmb = answer.image_answer.thumbnail.absolute_url
                    args = (thmb, answer.id,)
                    out.append('<img src="%s" id="img_%d" />' % args)
                    x_y = get_image_dimensions(answer.image_answer.file)
                except ThumbnailException as ex:
                    valid = False
                    out.append('<div class="error">%s</div>' % str(ex))
                thumb_width = Answer.image_answer_thumbnail_meta["size"][0]
                # This extra hidden input is in case you want to enlarge
                # images. Don't bother enlarging images unless we'll increase
                # their dimensions by at least 10%.
                if valid and x_y and float(x_y[0]) / thumb_width > 1.1:
                    format = ('<input type="hidden" id="img_%d_full_url" '
                              'value="%s" class="enlargeable" />')
                    enlarge = answer.image_answer
                    enlarge = enlarge.extra_thumbnails["max_enlarge"]
                    enlarge = enlarge.absolute_url
                    args = (answer.id, enlarge)
                    out.append(format % args)
            elif question.option_type == OPTION_TYPE_CHOICES.VIDEO:
                if oembed_expand:
                    html = video_html(answer.value, video_height, video_width)
                    out.append(html)
                else:
                    args = {"val": escape(answer.value)}
                    out.append('<a href="%(val)s">%(val)s</a>' % args)
            else:
                out.append(escape(answer.value))
            out.append('</div>')
    return mark_safe("\n".join(out))
register.simple_tag(submission_fields)


def video_html(vid, maxheight, maxwidth):
    key = "%s_%d_%d" % (vid, maxheight, maxwidth)
    value = cache.get(key, None)
    if not value:
        value = "Unable to find video %s." % escape(vid)
        try: 
            data = oembed_expand(vid, maxheight=maxheight, maxwidth=maxwidth)
            if data and 'html' in data:
                html = '<div class="videoplayer">%s</div>' % data['html']
                value = mark_safe(html)
        except Exception as ex:
            logging.warn("oembed_expand exception: %s" % str(ex))
        # This shouldn't really change and it's an expensive runtime lookup.
        # Cache it for a very long time.
        cache.set(key, value, 7 * 24 * 60 * 60)
    return value


DETAIL_SURVEY_NONE = ChoiceEnum('detail survey none')


def submissions(object_list, fields):
    out = []
    page_answers = get_all_answers(object_list)
    for submission in object_list:
        out.append('<div class="submission">')
        out.append(submission_fields(submission, fields, page_answers))
        D = link_detail_survey_none=DETAIL_SURVEY_NONE.DETAIL
        out.append(submission_link(submission, D))
        out.append('</div>')
    return mark_safe("\n".join(out))
register.simple_tag(submissions)


def submission_link(submission,
                    link_detail_survey_none=DETAIL_SURVEY_NONE.SURVEY):
    out = ['<div class="permalink">']
    if link_detail_survey_none == DETAIL_SURVEY_NONE.NONE:
        return ""
    elif link_detail_survey_none == DETAIL_SURVEY_NONE.SURVEY:
        text = "Back to %s" % submission.survey.title
        kwargs = {"slug": submission.survey.slug}
        view = "survey_default_report_page_1"
        if submission.survey.default_report:
            kwargs["report"] = submission.survey.default_report.slug
            view = "survey_report_page_1"
        url = reverse(view, kwargs=kwargs)
    elif link_detail_survey_none == DETAIL_SURVEY_NONE.DETAIL:
        url = submission.get_absolute_url()
        text = "Permalink"
    out.append('<a href="%s">%s</a>' % (url, text,))
    out.append('</div>')
    return mark_safe("\n".join(out))
register.simple_tag(submission_link)


def paginator(survey, report, pages_to_link, page_obj):
    out = []
    url_args = dict(slug=survey.slug, page=0)
    view_name = "survey_default_report"
    if report.slug:
        view_name = "survey_report"
        url_args["report"] = report.slug
    if len(pages_to_link) > 1:
        out.append('<div class="pages">')
        if page_obj.has_previous():
            url_args["page"] = page_obj.previous_page_number()
            url = reverse(view_name, kwargs=url_args)
            out.append('<a href="%s">&laquo; Previous</a>' % url)
        for page in pages_to_link:
            if not page:
                out.append("...")
            elif page_obj.number == page:
                out.append(str(page))
            else:
                url_args["page"] = page
                url = reverse(view_name, kwargs=url_args)
                out.append('<a href="%s">%d</a>' % (url, page))
        if page_obj.has_next():
            url_args["page"] = page_obj.next_page_number()
            url = reverse(view_name, kwargs=url_args)
            out.append('<a href="%s">Next &raquo;</a>' % url)
        out.append("</div>")
    return mark_safe("\n".join(out))
register.simple_tag(paginator)


def map_key(survey):
    option_icon_pairs = survey.parsed_option_icon_pairs()
    option_icon_pairs = [(o, i) for (o, i) in option_icon_pairs if i]
    out = []
    if option_icon_pairs:
        out.append('<ul class="map_key">')
        for (option, icon) in option_icon_pairs:
            format = '<li><img src="%s" alt="%s" /> %s</li>'
            out.append(format % (icon, option, option))
        out.append('</ul>')
    return mark_safe("\n".join(out))
register.simple_tag(map_key)


def number_to_javascript(number):
    if isinstance(number, (int, float,)):
        return str(number)
    return "null"


def issue(message):
    return mark_safe("<div class=\"issue\">%s</div>" % message)
register.simple_tag(issue)


def thanks_for_entering(request, forms, survey):
    if "POST" == request.method and all([f.is_valid() for f in forms]):
        message = survey.thanks or "Thanks for entering!"
        return mark_safe("<p>%s</p>" % message)
    return ""
register.simple_tag(thanks_for_entering)


def download_tags(survey):
    return mark_safe("\n".join([
        '<h2 class="chart_title">Download Results As...</h2>',
        '<p class="download_tags">%s</p>' % survey.get_download_tags()]))
register.simple_tag(download_tags)
