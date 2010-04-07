from django import template
from django.template import Node
from django.utils.safestring import mark_safe
from ..crowdsourcing.models import AggregateResult


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


def filters_as_ul(filters):
    if not filters:
        return ""
    out = ['<form method="GET">',
               '<ul class="filters">']
    out.extend([f.as_li() for f in filters])
    out.extend(['</ul>',
                    '<input type="submit" value="Submit" />',
                    '</form>'])
    return "\n".join(out)
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
    return "\n".join(out)
register.simple_tag(yahoo_pie_chart)


def submissions(object_list):
    out = []
    for submission in object_list:
        out.append('<div class="submission">')
        for question in fields:
            out.append('<div class="field">')
            answer = submission.answer_set.filter(question=question)
            if answer:
                answer = answer[0]
            if answer and answer.value:
                out.append('<label>%s</label>' % question.label)
                if answer.image_answer:
                    src = answer.image_answer.thumbnail.absolute_url
                    out.append('<img src="%s" />' % src)
                elif question.option_type == OPTION_TYPE_CHOICES.VIDEO_LINK:
                    # ${util.oembed_video(answer.value, 360, 288)}
                    out.append("TODO: oembed_video")
                else:
                    out.append(answer.value)
            out.append('</div>')
        out.append('</div>')
    return "\n".join(out)
register.simple_tag(submissions)


def paginator(survey, report, paginator_obj, page):
    out = []
    url_args = dict(slug=survey.slug, page=0)
    view_name = "survey_default_report"
    if report.slug:
        view_name = "survey_report"
        url_args["report"] = report.slug
    if paginator_obj.num_pages > 1:
        out.apend('<div class="pages">')
        if page_obj.has_previous():
            args["page"] = page_obj.previous_page_number()
            url = reverse(view_name, kwargs=url_args)
            out.append('<a href="%s">&laquo; Previous</a>' % url)
        for page in pages_to_link:
            if not page:
                out.append("...")
            elif page_obj.number == page:
                out.append(str(page))
            else:
                args["page"] = page
                url = reverse(view_name, kwargs=url_args)
                out.append('<a href="%s">%d</a>' % (url, page))
        if page_obj.has_next():
            args["page"] = page_obj.next_page_number()
            url = reverse(view_name, kwargs=url_args)
            out.append('<a href="%s">Next &raquo;</a>' % url)
        out.append("</div>")
    return "\n".join(out)
register.simple_tag(paginator)


"""def register_tag(process_function):
    def function_node_returner(parser, token):
        return FunctionNode(process_function, parser, token)
    return register.tag(function_node_returner)


class FunctionNode(Node):
    def __init__(self, process_function, parser=None, token=None):
        self.num_args = process_function.__code__.co_argcount
        if self.num_args:
            require_msg = "%s has arguments so parser and token are required."
            require_msg = require_msg % process_function.__code__.co_argcount
            assert parser and token, require_msg
            bits = token.split_contents()
            if len(bits) != 1 + self.num_args:
                error_args = (bits[0], self.num_args)
                raise TemplateSyntaxError(
                    "'%s' requires %d argument(s)." % error_args)
            self.raw_arguments = [parser.compile_filter(b) for b in bits[1:]]
        self.process_function = process_function

    def render(self, context):
        args = []
        if self.num_args:
            args = [a.resolve(context, True) for a in self.raw_arguments]
        return mark_safe(self.process_function(*args))"""
