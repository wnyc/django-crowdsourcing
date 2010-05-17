import logging

from django import template
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.template import Node
from django.utils.safestring import mark_safe
from django.utils.html import escape

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
Django templates. We provide every function as both a template tag and as
a function that returns a safe string. """


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


def select_filter(wrapper_format, label, key, value, choices, blank=True):
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


def filter_as_li(filter):
    output = []
    wrapper_format = "<li>%s</li>"
    if FILTER_TYPE.CHOICE == filter.type:
        output.append(select_filter(wrapper_format,
                                    filter.label,
                                    filter.key,
                                    filter.value,
                                    filter.choices))
    elif FILTER_TYPE.RANGE == filter.type:
        output.append(range_filter(wrapper_format,
                                   filter.key,
                                   filter.label,
                                   filter.from_value,
                                   filter.to_value))
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


def submission_fields(submission, fields, page_answers, video_height=360, video_width=288):
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
                src = answer.image_answer.thumbnail.absolute_url
                out.append('<img src="%s" />' % src)
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


def submissions(object_list, fields):
    out = []
    page_answers = get_all_answers(object_list)
    for submission in object_list:
        out.append('<div class="submission">')
        out.append(submission_fields(submission, fields, page_answers))
        out.append('</div>')
    return mark_safe("\n".join(out))
register.simple_tag(submissions)


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
