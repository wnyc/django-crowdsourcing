from __future__ import absolute_import


import datetime
import logging
from math import sin, cos
from operator import itemgetter
import simplejson
from textwrap import fill


from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models, connection
from django.db.models import Count
from django.db.models.fields.files import ImageFieldFile
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe


from .fields import ImageWithThumbnailsField
from .geo import get_latitude_and_longitude
from .util import ChoiceEnum
from . import settings as local_settings


try:
    from positions.fields import PositionField
except ImportError:
    logging.warn('positions not installed. '
                 'Will just use integers for position fields.')
    PositionField = None


try:
    from .flickrsupport import sync_to_flickr, get_group_id
except ImportError:
    logging.warn('no flickr support available')
    sync_to_flickr = None


ARCHIVE_POLICY_CHOICES = ChoiceEnum(('immediate',
                                     'post-close',
                                     'never'))


class LiveSurveyManager(models.Manager):
    def get_query_set(self):
        now = datetime.datetime.now()
        return super(LiveSurveyManager, self).get_query_set().filter(
            is_published=True,
            starts_at__lte=now).filter(
            ~models.Q(archive_policy__exact=ARCHIVE_POLICY_CHOICES.NEVER) |
            models.Q(ends_at__isnull=True) |
            models.Q(ends_at__gt=now))


class Survey(models.Model):
    title = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    tease = models.TextField(blank=True)
    description = models.TextField(blank=True)
    thanks = models.TextField(
        blank=True,
        help_text="When a user submits the survey, display this message.")

    require_login = models.BooleanField(default=False)
    allow_multiple_submissions = models.BooleanField(default=False)
    moderate_submissions = models.BooleanField(
        default=local_settings.MODERATE_SUBMISSIONS)
    allow_comments = models.BooleanField(
        default=False,
        help_text="Allow comments on user submissions.")
    allow_voting = models.BooleanField(
        default=False,
        help_text="Users can vote on submissions.")
    archive_policy = models.IntegerField(
        choices=ARCHIVE_POLICY_CHOICES,
        default=ARCHIVE_POLICY_CHOICES.IMMEDIATE)
    starts_at = models.DateTimeField(default=datetime.datetime.now)
    survey_date = models.DateField(blank=True, null=True, editable=False)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    email = models.CharField(
        max_length=255,
        blank=True,
        help_text=("Send a notification to these e-mail addresses whenever "
                   "someone submits an entry to this survey. Comma "
                   "delimited."))
    site = models.ForeignKey(Site)
    flickr_group_id = models.CharField(
        max_length=60,
        blank=True,
        editable=False)
    flickr_group_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Use the exact group name from flickr.com")
    default_report = models.ForeignKey(
        'SurveyReport',
        blank=True,
        null=True,
        related_name='reports',
        help_text=("Whenever we automatically generate a link to the results "
                   "of this survey we'll use this report. If it's left blank, "
                   "we'll use the default report behavior."))

    def to_jsondata(self):
        kwargs = {'slug': self.slug}
        submit_url = reverse('survey_detail', kwargs=kwargs)
        report_url = reverse('survey_default_report_page_1', kwargs=kwargs)
        questions = self.questions.order_by("order")
        return dict(title=self.title,
                    id=self.id,
                    slug=self.slug,
                    description=self.description,
                    tease=self.tease,
                    thanks=self.thanks,
                    submit_url=submit_url,
                    report_url=report_url,
                    questions=[q.to_jsondata() for q in questions])

    def save(self, **kwargs):
        self.survey_date = self.starts_at.date()
        self.flickr_group_id = ""
        if self.flickr_group_name and sync_to_flickr:
            self.flickr_group_id = get_group_id(self.flickr_group_name)
        super(Survey, self).save(**kwargs)

    class Meta:
        ordering = ('-starts_at',)
        unique_together = (('survey_date', 'slug'),)

    @property
    def is_open(self):
        now = datetime.datetime.now()
        if self.ends_at:
            return self.starts_at <= now < self.ends_at
        return self.starts_at <= now

    def get_public_fields(self, fieldnames=None):
        if not "_public_fields" in self.__dict__:
            questions = self.questions.filter(answer_is_public=True)
            questions = questions.select_related("survey")
            self.__dict__["_public_fields"] = list(questions.order_by("order"))
        fields = self.__dict__["_public_fields"]
        if fieldnames:
            return [f for f in fields if f.fieldname in fieldnames]
        return fields

    def get_public_archive_fields(self):
        types = (
            OPTION_TYPE_CHOICES.TEXT_FIELD,
            OPTION_TYPE_CHOICES.PHOTO_UPLOAD,
            OPTION_TYPE_CHOICES.VIDEO_LINK,
            OPTION_TYPE_CHOICES.TEXT_AREA)
        return [f for f in self.get_public_fields() if f.option_type in types]

    def icon_questions(self):
        OTC = OPTION_TYPE_CHOICES
        return self.questions.filter(
            ~models.Q(map_icons=""),
            option_type__in=[OTC.SELECT_ONE_CHOICE, OTC.RADIO_LIST])

    def parsed_option_icon_pairs(self):
        icon_questions = self.icon_questions()
        if icon_questions:
            return icon_questions[0].parsed_option_icon_pairs()
        return ()

    def submissions_for(self, user, session_key):
        q = models.Q(survey=self)
        if user.is_authenticated():
            q = q & models.Q(user=user)
        elif session_key:
            q = q & models.Q(session_key=session_key)
        else:
            # can't pinpoint user, return none
            return Submission.objects.none()
        return Submission.objects.filter(q)

    def can_have_public_submissions(self):
        return self.archive_policy != ARCHIVE_POLICY_CHOICES.NEVER and (
            self.archive_policy == ARCHIVE_POLICY_CHOICES.IMMEDIATE or
            not self.is_open)

    def public_submissions(self):
        if not self.can_have_public_submissions():
            return self.submission_set.none()
        return self.submission_set.filter(is_public=True)

    def featured_submissions(self):
        return self.public_submissions().filter(featured=True)

    def get_filters(self):
        return self.questions.filter(use_as_filter=True,
                                     answer_is_public=True,
                                     option_type__in=FILTERABLE_OPTION_TYPES)

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('survey_detail', (), {'slug': self.slug})

    objects = models.Manager()
    live = LiveSurveyManager()


OPTION_TYPE_CHOICES = ChoiceEnum(sorted([('char', 'Text Field'),
                                         ('email', 'Email Field'),
                                         ('photo', 'Photo Upload'),
                                         ('video', 'Video Link'),
                                         ('location', 'Location Field'),
                                         ('integer', 'Integer'),
                                         ('float', 'Float'),
                                         ('bool', 'Boolean'),
                                         ('text', 'Text Area'),
                                         ('select', 'Select One Choice'),
                                         ('radio', 'Radio List'),
                                         ('checkbox', 'Checkbox List')],
                                        key=itemgetter(1)))


FILTERABLE_OPTION_TYPES = (OPTION_TYPE_CHOICES.BOOLEAN,
                           OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE,
                           OPTION_TYPE_CHOICES.RADIO_LIST,
                           OPTION_TYPE_CHOICES.INTEGER,
                           OPTION_TYPE_CHOICES.FLOAT,
                           OPTION_TYPE_CHOICES.LOCATION_FIELD)


class Question(models.Model):
    survey = models.ForeignKey(Survey, related_name="questions")
    fieldname = models.CharField(
        max_length=32,
        help_text=_('a single-word identifier used to track this value; '
                    'it must begin with a letter and may contain '
                    'alphanumerics and underscores (no spaces). You must not '
                    'change this field on a live survey.'))
    question = models.TextField(help_text=_(
        "Appears on the survey entry page."))
    label = models.CharField(max_length=32, help_text=_(
        "Appears on the results page."))
    help_text = models.TextField(
        blank=True)
    required = models.BooleanField(
        default=False,
        help_text=_("Unsafe to change on live surveys."))
    if PositionField:
        order = PositionField(collection=('survey',))
    else:
        order = models.IntegerField()
    option_type = models.CharField(
        max_length=12,
        choices=OPTION_TYPE_CHOICES,
        help_text=_('You must not change this field on a live survey.'))
    options = models.TextField(
        blank=True,
        default='',
        help_text=_(
            'You can not safely modify this field once a survey has gone '
            'live. You can, at your own risk, add new options, but you '
            'must not change or remove options.'))
    map_icons = models.TextField(
        blank=True,
        default='',
        help_text=('Use one icon url per line. These should line up with the '
            'options. If the user\'s submission appears on a map, we\'ll use '
            'the corresponding icon on the map. This field only makes sense '
            'for Radio List and Select One Choice questions. Do not enter '
            'these map icons on a Location Field. For Google maps '
            'use 34px high by 20px wide .png images with a transparent '
            'background. You can safely modify this field on live surveys.'))
    answer_is_public = models.BooleanField(default=True)
    use_as_filter = models.BooleanField(default=True)
    _aggregate_result = None

    @property
    def is_filterable(self):
        return (self.use_as_filter and
                self.option_type in FILTERABLE_OPTION_TYPES)

    def to_jsondata(self):
        return dict(fieldname=self.fieldname,
                    label=self.label,
                    is_filterable=self.is_filterable,
                    question=self.question,
                    required=self.required,
                    option_type=self.option_type,
                    options=self.parsed_options,
                    answer_is_public=self.answer_is_public,
                    cms_id=self.id,
                    help_text=self.help_text)

    class Meta:
        ordering = ('order',)
        unique_together = ('fieldname', 'survey')

    def __unicode__(self):
        return self.question

    @property
    def parsed_options(self):
        if OPTION_TYPE_CHOICES.BOOLEAN == self.option_type:
            return [True, False]
        return filter(None, (s.strip() for s in self.options.splitlines()))

    @property
    def parsed_map_icons(self):
        return filter(None, (s.strip() for s in self.map_icons.splitlines()))

    def parsed_option_icon_pairs(self):
        options = self.parsed_options
        icons = self.parsed_map_icons
        to_return = []
        for i in range(len(options)):
            if i < len(icons):
                to_return.append((options[i], icons[i]))
            else:
                to_return.append((options[i], None))
        return to_return

    @property
    def value_column(self):
        ot = self.option_type
        if ot == OPTION_TYPE_CHOICES.BOOLEAN:
            return "boolean_answer"
        elif ot == OPTION_TYPE_CHOICES.FLOAT:
            return "float_answer"
        elif ot == OPTION_TYPE_CHOICES.INTEGER:
            return "integer_answer"
        elif ot == OPTION_TYPE_CHOICES.PHOTO_UPLOAD:
            return "image_answer"
        return "text_answer"


FILTER_TYPE = ChoiceEnum("choice range distance")


class Filter:
    def __init__(self, field, request_data):
        self.field = field
        self.key = field.fieldname
        self.label = field.label
        self.choices = field.parsed_options
        self.value = self.from_value = self.to_value = ""
        self.within_value = self.location_value = ""
        def get_val(suffix):
            return request_data.get(self.key + suffix, "").replace("+", " ")
        if field.option_type in (OPTION_TYPE_CHOICES.BOOLEAN,
                                 OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE,
                                 OPTION_TYPE_CHOICES.RADIO_LIST):
            self.type = FILTER_TYPE.CHOICE
            self.value = get_val("")
        elif field.option_type in (OPTION_TYPE_CHOICES.INTEGER,
                                   OPTION_TYPE_CHOICES.FLOAT):
            self.type = FILTER_TYPE.RANGE
            self.from_value = get_val("_from")
            self.to_value = get_val("_to")
        elif field.option_type == OPTION_TYPE_CHOICES.LOCATION_FIELD:
            self.type = FILTER_TYPE.DISTANCE
            self.within_value = get_val("_within")
            self.location_value = get_val("_location")


def get_filters(survey, request_data):
    fields = list(survey.get_public_fields())
    return [Filter(f, request_data) for f in fields if f.is_filterable]


def extra_from_filters(set, submission_id_column, survey, request_data):
    sid = submission_id_column
    for where, params in extra_clauses_from_filters(sid, survey, request_data):
        set = set.extra(where=[where], params=params)
    return set


def extra_clauses_from_filters(submission_id_column, survey, request_data):
    return_value = []
    for filter in get_filters(survey, request_data):
        loc = filter.location_value and filter.within_value
        if filter.value or filter.from_value or filter.to_value or loc:
            try:
                type = filter.field.option_type
                is_float = OPTION_TYPE_CHOICES.FLOAT == type
                is_integer = OPTION_TYPE_CHOICES.INTEGER == type
                is_distance = OPTION_TYPE_CHOICES.LOCATION_FIELD == type
                where = "".join((
                    submission_id_column,
                    " IN (SELECT submission_id FROM ",
                    "crowdsourcing_answer WHERE question_id = %d ",
                    "AND ")) % filter.field.id
                if OPTION_TYPE_CHOICES.BOOLEAN == filter.field.option_type:
                    f = ("0", "f",)
                    length = len(filter.value)
                    params = [length and not filter.value[0].lower() in f]
                    where += "boolean_answer = %s"
                elif is_float or is_integer:
                    convert = float if is_float else int
                    column = "float_answer" if is_float else "integer_answer"
                    params = []
                    wheres = []
                    if filter.from_value:
                        params.append(convert(filter.from_value))
                        wheres.append("%s <= " + column)
                    if filter.to_value:
                        params.append(convert(filter.to_value))
                        wheres.append(column + " <= %s")
                    where += " AND ".join(wheres)
                elif is_distance:
                    e = _extra_from_distance(filter, submission_id_column)
                    if e:
                        d_where, params = e
                        where += d_where
                    else:
                        break
                else:
                    params = [filter.value]
                    where += "text_answer = %s"
                where += ")"
                return_value.append((where, params,))
            except ValueError:
                pass
    return return_value


def _extra_from_distance(filter, submission_id_column):
    """ This uses the Spherical Law of Cosines for a close enough approximation
    of distances. distance = acos(sin(lat1) * sin(lat2) +
                                  cos(lat1) * cos(lat2) *
                                  cos(lng2 - lng1)) * 3959
    The "radius" of the earth varies between 3,950 and 3,963 miles. """
    key = "lat_lng_of_" + str(filter.location_value.lower())
    lat_lng = cache.get(key, None)
    if lat_lng is None:
        lat_lng = get_latitude_and_longitude(filter.location_value)
        cache.set(key, lat_lng)
    (lat, lng) = lat_lng
    if lat is None or lng is None:
        return
    acos_of_args = (
        sin(_radians(lat)),
        _D_TO_R,
        cos(_radians(lat)),
        _D_TO_R,
        lng,
        _D_TO_R)
    acos_of = (
        "%f * sin(latitude / %f) + "
        "%f * cos(latitude / %f) * "
        "cos((longitude - %f) / %f)") % acos_of_args
    where = "".join((
        submission_id_column,
        " IN (SELECT ca.submission_id FROM ",
        "crowdsourcing_answer AS ca JOIN crowdsourcing_submission AS cs ",
        "ON ca.submission_id = cs.id ",
        "WHERE cs.survey_id = %s AND latitude IS NOT NULL ",
        "AND longitude IS NOT NULL AND ",
        acos_of,
        " < 1 AND 3959.0 * acos(",
        acos_of,
        ") <= %s)"))
    params = [int(filter.field.survey_id), int(filter.within_value)]
    return where, params


_D_TO_R = 57.295779


def _radians(degrees):
    return degrees / _D_TO_R


class AggregateResultCount:
    """ This helper class makes it easier to write templates that display
    aggregate results. """
    def __init__(self, survey, field, request_data):
        self.answer_set = field.answer_set.values('text_answer',
                                                  'boolean_answer')
        self.answer_set = self.answer_set.annotate(count=Count("id"))
        self.answer_set = extra_from_filters(self.answer_set,
                                             "submission_id",
                                             survey,
                                             request_data)
        self.answer_counts = []
        for answer in self.answer_set:
            if field.option_type == OPTION_TYPE_CHOICES.BOOLEAN:
                text = str(answer["boolean_answer"])
            else:
                text = fill(answer["text_answer"], 30)
            if answer["count"]:
                self.answer_counts.append({
                    "response": text,
                    "count": answer["count"]})
        self.yahoo_answer_string = simplejson.dumps(self.answer_counts)


class AggregateResultSum:
    def __init__(self, y_axes, x_axis, request_data):
        self.answer_sums = []
        answer_sum_lookup = {}

        def new_answer_sum(x_value):
            answer_sum = {x_axis.fieldname: x_value}
            for y_axis in y_axes:
                answer_sum[y_axis.fieldname] = 0
            answer_sum_lookup[x_value] = answer_sum
            self.answer_sums.append(answer_sum)
            return answer_sum

        # We could just add new x-axis values as we encounter them. However,
        # say someone has parsed_options ["January", ... , "December"].
        # Then doing it this way puts them in order.
        [new_answer_sum(x_value) for x_value in x_axis.parsed_options]

        x_value_column = "x_axis." + x_axis.value_column
        for y_axis in y_axes:
            params = [y_axis.id, x_axis.id]
            y_axis_column = y_axis.value_column
            if "boolean_answer" == y_axis_column:
                y_axis_column = "CAST(y_axis." + y_axis_column + " AS int)"
            else:
                y_axis_column = "y_axis." + y_axis_column
            query = [
                "SELECT ",
                x_value_column,
                " AS x_value, SUM(",
                y_axis_column,
                ") AS y_value FROM crowdsourcing_answer AS y_axis ",
                "JOIN crowdsourcing_answer AS x_axis "
                "ON y_axis.submission_id = x_axis.submission_id ",
                "WHERE y_axis.question_id = %s ",
                "AND x_axis.question_id = %s"]
            y = "y_axis.submission_id"
            extras = extra_clauses_from_filters(y, x_axis.survey, request_data)
            for where, next_params in extras:
                query.append(" AND ")
                query.append(where)
                params += next_params
            query.append(" GROUP BY ")
            query.append(x_value_column)
            cursor = connection.cursor()
            cursor.execute("".join(query), params)
            for x_value, y_value in cursor.fetchall():
                answer_sum = answer_sum_lookup.get(x_value)
                if not answer_sum:
                    answer_sum = new_answer_sum(x_value)
                answer_sum[y_axis.fieldname] += y_value
        self.yahoo_answer_string = simplejson.dumps(self.answer_sums)


class Submission(models.Model):
    survey = models.ForeignKey(Survey)
    user = models.ForeignKey(User, null=True)
    ip_address = models.IPAddressField()
    submitted_at = models.DateTimeField(default=datetime.datetime.now)
    session_key = models.CharField(max_length=40, blank=True, editable=False)
    featured = models.BooleanField(default=False)

    # for moderation
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ('-submitted_at',)

    def to_jsondata(self):
        def to_json(v):
            if isinstance(v, ImageFieldFile):
                return v.url if v else ''
            return v
        return_value = dict(data=dict((a.question.fieldname, to_json(a.value))
                                      for a in self.answer_set.filter(
                                      question__answer_is_public=True)),
                            survey=self.survey.slug,
                            submitted_at=self.submitted_at,
                            featured=self.featured)
        if self.user:
            return_value["user"] = self.user.username
        return return_value

    def get_answer_dict(self):
        try:
            # avoid called __getattr__
            return self.__dict__['_answer_dict']
        except KeyError:
            answers = self.answer_set.all()
            d = dict((a.question.fieldname, a.value) for a in answers)
            self.__dict__['_answer_dict'] = d
            return d

    def items(self):
        return self.get_answer_dict().items()

    def get_absolute_url(self):
        view = 'crowdsourcing.views.submission'
        return reverse(view, kwargs={"id": self.pk})

    @property
    def email(self):
        return self.get_answer_dict().get('email', '')


class Answer(models.Model):
    submission = models.ForeignKey(Submission)
    question = models.ForeignKey(Question)
    text_answer = models.TextField(blank=True)
    integer_answer = models.IntegerField(null=True)
    float_answer = models.FloatField(null=True)
    boolean_answer = models.NullBooleanField()
    image_answer = ImageWithThumbnailsField(
        max_length=500,
        blank=True,
        thumbnail=dict(size=(250, 250)),
        upload_to=local_settings.IMAGE_UPLOAD_PATTERN)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    flickr_id = models.CharField(max_length=64, blank=True)
    photo_hash = models.CharField(max_length=40,
                                  null=True,
                                  blank=True,
                                  editable=False)

    def value():
        def get(self):
            return getattr(self, self.question.value_column)

        def set(self, v):
            ot = self.question.option_type
            if ot == OPTION_TYPE_CHOICES.BOOLEAN:
                self.boolean_answer = bool(v)
            elif ot == OPTION_TYPE_CHOICES.FLOAT:
                self.float_answer = float(v)
            elif ot == OPTION_TYPE_CHOICES.INTEGER:
                self.integer_answer = int(v)
            elif ot == OPTION_TYPE_CHOICES.PHOTO_UPLOAD:
                self.image_answer = v
            else:
                self.text_answer = v

        return get, set
    value = property(*value())

    class Meta:
        ordering = ('question',)

    def save(self, **kwargs):
        super(Answer, self).save(**kwargs)
        # or should this be in a signal?  Or build in an option
        # to manage asynchronously? @TBD
        if sync_to_flickr:
            survey = self.question.survey
            if survey.flickr_group_id:
                try:
                    sync_to_flickr(self, survey.flickr_group_id)
                except Exception as ex:
                    message = "error in syncing to flickr: %s" % str(ex)
                    logging.exception(message)

    def __unicode__(self):
        return unicode(self.question)


class SurveyReport(models.Model):
    """
    a survey report permits the presentation of data submitted in a
    survey to be customized.  It consists of a series of display
    options, which each take a display type, a series of fieldnames,
    and an annotation.  It also has article-like fields of its own.
    """
    survey = models.ForeignKey(Survey)
    title = models.CharField(max_length=50, blank=True)
    slug = models.CharField(max_length=50, blank=True)
    # some text at the beginning
    summary = models.TextField(blank=True)
    # As crowdsourcing doesn't implement rating because we want to let you use
    # your own, we don't actually use this flag anywhere in the crowdsourcing
    # project. Rather, see settings.PRE_REPORT
    sort_by_rating = models.BooleanField(
        default=False,
        help_text="By default, sort descending by highest rating. Otherwise, "
                  "the default sort is by date descending.")
    display_the_filters = models.BooleanField(
        default=True,
        help_text="Display the filters at the top of the report page.")
    limit_results_to = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Only use the top X submissions.")
    display_individual_results = models.BooleanField(
        default=True,
        help_text="Display separate, individual results if this field is True "
                  "and you have archivable questions, like those with "
                  "paragraph answers.")
    # A useful variable for holding different report displays so they don't
    # get saved to the database.
    survey_report_displays = None

    def get_survey_report_displays(self):
        if self.pk and self.survey_report_displays is None:
            srds = list(self.surveyreportdisplay_set.select_related('report'))
            self.survey_report_displays = srds
            for srd in self.survey_report_displays:
                srd._report = self
        return self.survey_report_displays

    def has_display_type(self, type):
        if not hasattr(type, '__iter__'):
            type = [type]
        displays = self.get_survey_report_displays()
        return bool([1 for srd in displays if srd.display_type in type])

    def has_charts(self):
        SRDC = SURVEY_DISPLAY_TYPE_CHOICES
        return self.has_display_type([SRDC.PIE, SRDC.BAR, SRDC.LINE])

    @models.permalink
    def get_absolute_url(self):
        return ('survey_report', (), {'slug': self.survey.slug,
                                      'report': self.slug})

    class Meta:
        unique_together = (('survey', 'slug'),)
        ordering = ('title',)

    def __unicode__(self):
        return self.title


SURVEY_DISPLAY_TYPE_CHOICES = ChoiceEnum('text pie map bar line')


class SurveyReportDisplay(models.Model):
    """ Think of this as a line item of SurveyReport. """
    report = models.ForeignKey(SurveyReport)
    display_type = models.PositiveIntegerField(
        choices=SURVEY_DISPLAY_TYPE_CHOICES)
    fieldnames = models.TextField(
        blank=True,
        help_text=_("Separate by spaces. These are the y-axis of bar and line "
                    "charts."))
    x_axis_fieldname = models.CharField(
        blank=True,
        help_text=_("This only applies to bar and line charts. Use only 1 "
                    "field."),
        max_length=80)
    annotation = models.TextField(blank=True)
    limit_map_answers = models.IntegerField(
        null=True,
        blank=True,
        help_text=_('Google maps gets pretty slow if you add too many points. '
                    'Use this field to limit the number of points that '
                    'display on the map.'))
    map_center_latitude = models.FloatField(
        blank=True,
        null=True,
        help_text=_('If you don\'t specify latitude, longitude, or zoom, the '
                    'map will just center and zoom so that the map shows all '
                    'the points.'))
    map_center_longitude = models.FloatField(blank=True, null=True)
    map_zoom = models.IntegerField(
        blank=True,
        null=True,
        help_text=_('13 is about the right level for Manhattan. 0 shows the '
                    'entire world.'))
    if PositionField:
        order = PositionField(collection=('report',))
    else:
        order = models.IntegerField()

    def questions(self, fields=None):
        return self._get_questions(self.fieldnames, fields)

    def x_axis_question(self, fields=None):
        return_value = self._get_questions(self.x_axis_fieldname, fields)
        if return_value:
            return return_value[0]
        return None

    def _get_questions(self, fieldnames, fields):
        names = fieldnames.split(" ")
        if fields:
            return [f for f in fields if f.fieldname in names]
        return self.get_report().survey.get_public_fields(names)

    def get_report(self):
        if hasattr(self, '_report'):
            return self._report
        return self.report

    def index_in_report(self):
        assert self.report, "This display's report attribute is not set."
        srds = self.get_report().get_survey_report_displays()
        for i in range(len(srds)):
            if srds[i] == self:
                return i
        assert False, "This display isn't in its report's displays."

    class Meta:
        ordering = ('order',)


    def __getattribute__(self, key):
        """ We provide is_text, is_pie, etc... as attirbutes to make it easier
        to write conditional logic in Django templates based on
        display_type."""
        if "is_" == key[:3]:
            for value, name in SURVEY_DISPLAY_TYPE_CHOICES._choices:
                if name == key[3:]:
                    return self.display_type == value
        return super(SurveyReportDisplay, self).__getattribute__(key)


def get_all_answers(submission_list):
    ids = [submission.id for submission in submission_list]
    page_answers_list = Answer.objects.filter(submission__id__in=ids)
    page_answers_list = page_answers_list.select_related("question")
    page_answers = {}
    for answer in page_answers_list:
        if not answer.submission_id in page_answers:
            page_answers[answer.submission_id] = []
        page_answers[answer.submission_id].append(answer)
    return page_answers
