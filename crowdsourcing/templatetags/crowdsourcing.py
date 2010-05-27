import logging

from django import template
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.template import Node
from django.utils.safestring import mark_safe
from django.utils.html import escape
from sorl.thumbnail.base import ThumbnailException

from ..crowdsourcing.models import (AggregateResult, FILTER_TYPE,
                                    OPTION_TYPE_CHOICES, get_all_answers)
from ..crowdsourcing.util import ChoiceEnum, get_function
from ..crowdsourcing import settings as local_settings

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


def yahoo_pie_chart_header():
    return "\n".join([
        '<link rel="stylesheet" type="text/css" href="http://yui.yahooapis.com/2.8.0r4/build/fonts/fonts-min.css" />',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/yahoo-dom-event/yahoo-dom-event.js"></script>',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/json/json-min.js"></script>',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/element/element-min.js"></script>',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/datasource/datasource-min.js"></script>',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/swf/swf-min.js"></script>',
        '<script type="text/javascript" src="http://yui.yahooapis.com/2.8.0r4/build/charts/charts-min.js"></script>',
        '<style>',
        '  .chart_div { width: 600px; height: 300px; }',
        '</style>'])
register.simple_tag(yahoo_pie_chart_header)


def filter(wrapper_format, key, label, html):
    label_html = '<label for="%s">%s</label>' % (key, label,)
    return mark_safe(wrapper_format % (label_html + html))
register.simple_tag(filter)


def select_filter(wrapper_format, key, label, value, choices, blank=True):
    html = ['<select id="%s" name="%s">' % (key, key,)]
    if blank:
        html.append('<option value="">---------</option>')
    for choice in choices:
        html.append('<option value="%s"' % choice)
        if value == u"%s" % choice:
            html.append('selected="selected"')
        html.append('>%s</option>' % choice)
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


def yahoo_pie_chart(display, question, request_get):
    out = []
    aggregate = AggregateResult(question, request_get)
    if aggregate.answer_counts:
        out.extend([
            '<h2 class="chart_title">%s</h2>' % display.annotation,
            '<div class="chart_div" id="chart%d">' % question.id,
            'Unable to load Flash content. The YUI Charts Control ',
            'requires Flash Player 9.0.45 or higher. You can install the ',
            'latest version at the ',
            '<a href="http://www.adobe.com/go/getflashplayer">',
            'Adobe Flash Player Download Center</a>.',
            '</div>'])
        args = {
            "answer_string": aggregate.yahoo_answer_string,
            "data_var": 'data%d' % question.id,
            "question_id": question.id}
        script = """
            <script type="text/javascript">
              YAHOO.widget.Chart.SWFURL =
                "http://yui.yahooapis.com/2.8.0r4/build/charts/assets/charts.swf";
              var answerData = %(answer_string)s;
              var %(data_var)s = new YAHOO.util.DataSource(answerData);
              %(data_var)s.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
              %(data_var)s.responseSchema = {fields: [ "response", "count" ]};

              var chart%(question_id)d = new YAHOO.widget.PieChart(
                "chart%(question_id)d",
                data%(question_id)d,
                {dataField: "count",
                 categoryField: "response",
                 expressInstall: "assets/expressinstall.swf",
                 style: {padding: 20,
                         legend: {display: "right",
                                  padding: 10,
                                  spacing: 5,
                                  font: {family: "Arial",
                                         size: 13
                                        }
                                 }
                        }
                });
            </script>""" % args
        out.append(script)
    return mark_safe("\n".join(out))
register.simple_tag(yahoo_pie_chart)


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


def submission_fields(submission,
                      fields=None,
                      page_answers=None,
                      video_height=360,
                      video_width=288):
    if not page_answers:
        page_answers = get_all_answers([submission])
    if not fields:
        fields = list(submission.survey.get_public_fields())
    out = []
    answer_list = page_answers[submission.id]
    answers = {}
    for answer in answer_list:
        answers[answer.question] = answer
    for question in fields:
        out.append('<div class="field">')
        answer = answers.get(question, None)
        if answer and answer.value:
            out.append('<label>%s</label>' % question.label)
            if answer.image_answer:
                try:
                    thmb = answer.image_answer.thumbnail.absolute_url
                    args = (thmb, answer.id,)
                    out.append('<img src="%s" id="img_%d" />' % args)
                    # This extra hidden input is in case you want to enlarge
                    # images. Don't bother enlarging images unless we'll
                    # increase their dimensions by at least 10%.
                    thumb_width = answer.image_answer.thumbnail.width()
                    if float(answer.image_answer.width) / thumb_width > 1.1:
                        format = ('<input type="hidden" id="img_%d_full_url" '
                                  'value="%s" class="enlargeable" />')
                        args = (answer.id, answer.image_answer.url)
                        out.append(format % args)
                except ThumbnailException as ex:
                    out.append('<div class="error">%s</div>' % str(ex))
            elif question.option_type == OPTION_TYPE_CHOICES.VIDEO_LINK:
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


DETAIL_SURVEY_NONE = ChoiceEnum('detail survey none')


def submissions(object_list, fields):
    out = []
    page_answers = get_all_answers(object_list)
    for submission in object_list:
        out.append('<div class="submission">')
        out.append(submission_fields(submission, fields, page_answers))
        out.append(submission_link(submission, link_detail_survey_none=DETAIL_SURVEY_NONE.DETAIL))
        out.append('</div>')
    return mark_safe("\n".join(out))
register.simple_tag(submissions)


def submission_link(submission, link_detail_survey_none=DETAIL_SURVEY_NONE.SURVEY):
    out = ['<div class="permalink">']
    if link_detail_survey_none == DETAIL_SURVEY_NONE.NONE:
        return ""
    elif link_detail_survey_none == DETAIL_SURVEY_NONE.SURVEY:
        url = submission.get_absolute_url()
        text = "Permalink"
    elif link_detail_survey_none == DETAIL_SURVEY_NONE.DETAIL:
        text = "Back to %s" % submission.survey.title
        kwargs = {"slug": submission.survey.slug}
        view = "survey_default_report_page_1"
        if submission.survey.default_report:
            kwargs["report"] = submission.survey.default_report.slug
            view = "survey_report_page_1"
        url = reverse(view, kwargs=kwargs)
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


def google_maps_header():
    format = "\n".join([
        '<script',
        'src="http://maps.google.com/maps?file=api&amp;v=2&amp;sensor=false&amp;key=%s"',
        'type="text/javascript"></script>',
        '<script type="text/javascript">',
        '  $(window).unload(GUnload);',
        '</script>'])
    return format % local_settings.GOOGLE_MAPS_API_KEY
register.simple_tag(google_maps_header)


def google_map(display, question, request_GET, ids):
    map_id = "map_%d" % question.id
    detail_id = "map_detail_%d" % question.id
    view = "location_question_results"
    kwargs = {"question_id": question.pk}
    if ids:
        view = "location_question_results_ids"
        kwargs["submission_ids"] = ids
        if display.limit_map_answers:
            split = ids.split(",")[:display.limit_map_answers]
            kwargs["submission_ids"] = ",".join(split)
    elif display.limit_map_answers:
        view = "location_question_results_limit"
        kwargs["limit_map_answers"] = display.limit_map_answers
    data_url = reverse(view, kwargs=kwargs)
    img = '<img class="loading" src="/media/img/loading.gif" alt="loading" />'
    lat = number_to_javascript(display.map_center_latitude)
    lng = number_to_javascript(display.map_center_longitude)
    zoom = number_to_javascript(display.map_zoom)
    map_args = (map_id, detail_id, data_url, lat, lng, zoom)
    out = [
        '<div class="google_map_wrapper">',
        '  <div id="%s" class="google_map">' % map_id,
        '    ' + img,
        '  </div>',
        '  <div id="%s" class="map_story"></div>' % detail_id,
        '  <script type="text/javascript">',
        '    loadMap("%s", "%s", "%s", %s, %s, %s);' % map_args,
        '  </script>',
        '</div>']
    out.append(map_key(question.survey))
    return mark_safe("\n".join(out))
register.simple_tag(google_map)


def number_to_javascript(number):
    if isinstance(number, (int, float,)):
        return str(number)
    return "null"

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
