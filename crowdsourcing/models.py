from __future__ import absolute_import

import datetime
import logging
from operator import itemgetter

from django.contrib.auth.models import User
from django.db import models

from .geo import get_latitude_and_longitude
from .util import ChoiceEnum

ARCHIVE_POLICY_CHOICES=ChoiceEnum(('immediate',
                                   'post-close',
                                   'never'))

OPTION_REQUIREMENT_CHOICES=ChoiceEnum(("not presented",
                                       "optional",
                                       "required"))

class LiveSurveyManager(models.Manager):
    def get_query_set(self):
        now=datetime.datetime.now()
        return super(SurveyManager, self).get_query_set().filter(
            is_published=True,
            starts_at__lte=now).filter(
            ~models.Q(archive_policy__exact=ARCHIVE_POLICY_CHOICES.NEVER) | 
            models.Q(ends_at__isnull=True) |
            models.Q(ends_at__gt=now))


class Survey(models.Model):
    title=models.CharField(max_length=80)
    slug=models.SlugField(unique=True)
    tease=models.CharField(max_length=100)
    description=models.TextField(blank=True)
    require_login=models.BooleanField(default=False)
    allow_multiple_submits=models.BooleanField(default=False)

    ask_for_email=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                      default=OPTION_REQUIREMENT_CHOICES.REQUIRED)
    ask_for_title=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                      default=OPTION_REQUIREMENT_CHOICES.REQUIRED)
    ask_for_story=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                      default=OPTION_REQUIREMENT_CHOICES.OPTIONAL)
    ask_for_location=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                         default=OPTION_REQUIREMENT_CHOICES.OPTIONAL)
    ask_for_photo=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                      default=OPTION_REQUIREMENT_CHOICES.OPTIONAL)
    ask_for_video=models.IntegerField(choices=OPTION_REQUIREMENT_CHOICES,
                                      default=OPTION_REQUIREMENT_CHOICES.OPTIONAL)

    archive_policy=models.results=models.IntegerField(choices=ARCHIVE_POLICY_CHOICES,
                                                      default=ARCHIVE_POLICY_CHOICES.IMMEDIATE)

    starts_at=models.DateTimeField(default=datetime.datetime.now)
    survey_date=models.DateField(blank=True, null=True, editable=False)
    ends_at=models.DateTimeField(null=True, blank=True)
    is_published=models.BooleanField(default=False)

    # Flickr integration
    flickr_set_id=models.CharField(max_length=60, blank=True)

    def save(self, **kwargs):
        self.survey_date=self.starts_at.date()
        super(Survey, self).save(**kwargs)

    class Meta:
        ordering=('-starts_at',)
        unique_together=(('survey_date', 'slug'),)

    @property
    def is_open(self):
        now=datetime.datetime.now()
        if self.ends_at:
            return self.starts_at <= now < self.ends_at
        else:
            return self.starts_at <= now

    def submissions_for(user, session_key):
        q=models.Q(survey=survey)
        if user.is_authenticated():
            q=q & models.Q(user=user)
        elif session_key:
            q=q & models.Q(session_key=session_key)
        else:
            # can't pinpoint user, return none
            return Submission.objects.none()
        return Submission.objects.filter(q)


          

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('survey_detail', (), {'survey_slug': self.slug })

    objects=models.Manager()
    live=LiveSurveyManager()
    
OPTION_TYPE_CHOICES = ChoiceEnum(sorted([('char', 'Text Field'),
                                         ('integer', 'Integer'),
                                         ('float', 'Float'),
                                         ('bool', 'Boolean'),
                                         ('text', 'Text Area'),
                                         ('select', 'Select One Choice'),
                                         ('radio', 'Radio List'),
                                         ('checkbox', 'Checkbox List'),],
                                        key=itemgetter(1)))
                                 
class Question(models.Model):
    survey=models.ForeignKey(Survey)
    question=models.TextField()
    required=models.BooleanField(default=False)
    order=models.IntegerField(null=True, blank=True)
    option_type=models.CharField(max_length=12, choices=OPTION_TYPE_CHOICES)
    options=models.TextField(blank=True, default='')
    answer_is_public=models.BooleanField(default=True)

    class Meta:
        ordering=('order',)
        verbose_name="additional question"

    def __unicode__(self):
        return self.question

class Submission(models.Model):
    survey=models.ForeignKey(Survey)
    user=models.ForeignKey(User, null=True)
    email=models.EmailField(blank=True, null=True)
    ip_address=models.IPAddressField()
    submitted_at=models.DateTimeField(default=datetime.datetime.now)
    session_key=models.CharField(max_length=40, blank=True, editable=False)

    # basic fields
    title=models.CharField(max_length=128, blank=True)
    story=models.TextField(blank=True)
    photo=models.ImageField(max_length=400, null=True, blank=True, upload_to="crowdsource/%Y/%m/%d")
    video_url=models.URLField(max_length=300, blank=True, verify_exists=False)
    address=models.CharField(max_length=200, blank=True, null=True)
    latitude=models.FloatField(blank=True, null=True)
    longitude=models.FloatField(blank=True, null=True)

    # for moderation
    is_public=models.BooleanField(default=True)
    
    def save(self, **kwargs):
        if not (self.latitude or self.longitude) and (self.address):
            try:
                self.latitude, self.longitude=get_latitude_and_longitude(self.address)
            except:
                logging.exception("An error occurred trying to geocode address %s" % (self.address))
        super(Submission, self).save(**kwargs)

class Answer(models.Model):
    submission=models.ForeignKey(Submission)
    question=models.ForeignKey(Question)
    text_answer=models.TextField(blank=True)
    integer_answer=models.IntegerField(null=True)
    float_answer=models.FloatField(null=True)
    boolean_answer=models.NullBooleanField()

    class Meta:
        ordering=('question',)
    
    
