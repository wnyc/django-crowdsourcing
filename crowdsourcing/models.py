from __future__ import absolute_import

import datetime
import logging
from operator import itemgetter
import simplejson
from textwrap import fill

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import Count
from django.db.models.fields.files import ImageFieldFile
from django.utils.translation import ugettext_lazy as _
from djview import reverse

from .fields import ImageWithThumbnailsField
from .geo import get_latitude_and_longitude
from .util import ChoiceEnum
from . import settings as local_settings

from positions.fields import PositionField

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

    require_login = models.BooleanField(default=False)
    allow_multiple_submissions = models.BooleanField(default=False)
    moderate_submissions = models.BooleanField(
        default=local_settings.MODERATE_SUBMISSIONS)
    archive_policy = models.IntegerField(
        choices=ARCHIVE_POLICY_CHOICES,
        default=ARCHIVE_POLICY_CHOICES.IMMEDIATE)
    starts_at = models.DateTimeField(default=datetime.datetime.now)
    survey_date = models.DateField(blank=True, null=True, editable=False)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    site = models.ForeignKey(Site)
    flickr_group_id = models.CharField(
        max_length=60,
        blank=True,
        editable=False)
    flickr_group_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Use the exact group name from flickr.com")

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

    def get_public_fields(self):
        return self.questions.filter(answer_is_public=True)

    def get_public_location_fields(self):
        return self.questions.filter(
            option_type=OPTION_TYPE_CHOICES.LOCATION_FIELD,
            answer_is_public=True)

    def get_public_archive_fields(self):
        return self.questions.filter(
            option_type__in=(OPTION_TYPE_CHOICES.TEXT_FIELD,
                             OPTION_TYPE_CHOICES.PHOTO_UPLOAD,
                             OPTION_TYPE_CHOICES.VIDEO_LINK,
                             OPTION_TYPE_CHOICES.TEXT_AREA),
            answer_is_public=True)

    def get_public_aggregate_fields(self):
        return self.questions.filter(
            option_type__in=(OPTION_TYPE_CHOICES.INTEGER,
                             OPTION_TYPE_CHOICES.FLOAT,
                             OPTION_TYPE_CHOICES.BOOLEAN,
                             OPTION_TYPE_CHOICES.SELECT_ONE_CHOICE,
                             OPTION_TYPE_CHOICES.RADIO_LIST,
                             OPTION_TYPE_CHOICES.CHECKBOX_LIST),
            answer_is_public=True).order_by("order")

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
                           OPTION_TYPE_CHOICES.CHECKBOX_LIST)


class Question(models.Model):
    survey = models.ForeignKey(Survey, related_name="questions")
    fieldname = models.CharField(
        max_length=32,
        help_text=_('a single-word identifier used to track this value; '
                    'it must begin with a letter and may contain '
                    'alphanumerics and underscores (no spaces).'))
    question = models.TextField(help_text=_(
        "Appears on the survey entry page."))
    label = models.CharField(max_length=32, help_text=_(
        "Appears on the results page."))
    help_text = models.TextField(blank=True)
    required = models.BooleanField(default=False)
    order = PositionField(collection=('survey',))
    option_type = models.CharField(max_length=12, choices=OPTION_TYPE_CHOICES)
    options = models.TextField(blank=True, default='')
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
        return filter(None, (s.strip() for s in self.options.splitlines()))

    def aggregate_result(self):
        if None == self._aggregate_result:
            self._aggregate_result = AggregateResult(self)
        return self._aggregate_result

class AggregateResult:
    """ This helper class makes it easier to write templates that display
    aggregate results. """
    def __init__(self, field):
        self.answer_set = field.answer_set.values('text_answer')
        self.answer_set = self.answer_set.annotate(count=Count("id"))
        answer_counts = []
        for answer in self.answer_set:
            text = fill(answer["text_answer"], 30)
            answer_counts.append({"response": text, "count": answer["count"]})
        self.yahoo_answer_string = simplejson.dumps(answer_counts)


class Submission(models.Model):
    survey = models.ForeignKey(Survey)
    user = models.ForeignKey(User, null=True)
    ip_address = models.IPAddressField()
    submitted_at = models.DateTimeField(default=datetime.datetime.now)
    session_key = models.CharField(max_length=40, blank=True, editable=False)

    # for moderation
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ('-submitted_at',)

    def to_jsondata(self):

        def to_json(v):
            if isinstance(v, ImageFieldFile):
                return v.url if v else ''
            return v
        return dict(data=dict(
            (a.question.fieldname, to_json(a.value))
            for a in self.answer_set.filter(question__answer_is_public=True)),
                    submitted_at=self.submitted_at)

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

    def __getattr__(self, k):
        d = self.get_answer_dict()
        try:
            return d[k]
        except KeyError:
            raise AttributeError("no such attribute: %s" % k)

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
            ot = self.question.option_type
            if ot == OPTION_TYPE_CHOICES.BOOLEAN:
                return self.boolean_answer
            elif ot == OPTION_TYPE_CHOICES.FLOAT:
                return self.float_answer
            elif ot == OPTION_TYPE_CHOICES.INTEGER:
                return self.integer_answer
            elif ot == OPTION_TYPE_CHOICES.PHOTO_UPLOAD:
                return self.image_answer
            return self.text_answer

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
    # A useful variable for holding different report displays so they don't
    # get saved to the database.
    survey_report_displays = None

    @models.permalink
    def get_absolute_url(self):
        return ('survey_report', (), {'slug': self.survey.slug,
                                      'report': self.slug})
    
    class Meta:
        unique_together = (('survey', 'slug'),)
        ordering = ('title',)

    def __unicode__(self):
        return self.title


SURVEY_DISPLAY_TYPE_CHOICES = ChoiceEnum('text pie bar grid map')


class SurveyReportDisplay(models.Model):
    report = models.ForeignKey(SurveyReport)
    display_type = models.PositiveIntegerField(
        choices=SURVEY_DISPLAY_TYPE_CHOICES)
    fieldnames = models.TextField(blank=True, help_text="Separate by spaces.")
    annotation = models.TextField(blank=True)
    order = PositionField(collection=('report',))

    def questions(self):
        names = self.fieldnames.split(" ")
        return self.report.survey.questions.filter(fieldname__in=names)
