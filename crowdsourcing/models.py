from __future__ import absolute_import

import datetime
from operator import itemgetter

from django.contrib.auth.models import User
from django.db import models

from .geo import get_latitude_and_longitude
from .util import ChoiceEnum

class LiveSurveyManager(models.Manager):
    def get_query_set(self):
        now=datetime.datetime.now()
        return super(SurveyManager, self).get_query_set().filter(
            is_published=True,
            starts_at__lte=now).filter(
            models.Q(ends_at__isnull=True) |
            models.Q(ends_at__gt=now))


class Survey(models.Model):
  title=models.CharField(max_length=80)
  slug=models.SlugField(unique=True)
  tease=models.CharField(max_length=100)
  description=models.TextField(blank=True)
  require_login=models.BooleanField(default=False)
  allow_multiple_submits=models.BooleanField(default=False)
  starts_at=models.DateTimeField(default=datetime.datetime.now)
  survey_date=models.DateField(blank=True, null=True, editable=False)
  ends_at=models.DateTimeField(null=True, blank=True)
  is_published=models.BooleanField(default=False)

  def save(self, **kwargs):
      self.survey_date=self.starts_at.date()
      super(Survey, self).save(**kwargs)

  class Meta:
      ordering=('-starts_at')
      unique_together=(('survey_date', 'slug'),)

  def __unicode__(self):
      return self.title

  @models.permalink
  def get_absolute_url(self):
      return ('survey-detail', (), {'survey_slug': self.slug })

  objects=models.Manager()
  live=LiveSurveyManager()



OPTION_TYPE_CHOICES = ChoiceEnum(sorted([('char', 'Text Field'),
                                         ('integer', 'Integer'),
                                         ('float', 'Float'),
                                         ('bool', 'Boolean'),
                                         ('text', 'Text Area'),
                                         ('select', 'Select One Choice'),
                                         ('radio', 'Radio List'),
                                         ('checkbox', 'Checkbox List'),
                                         ('file', 'File Upload'),
                                         ('address', 'Address')],
                                        key=itemgetter(1)))
                                 
class Question(models.Model):
    survey=models.ForeignKey(Survey)
    question=models.TextField()
    required=models.BooleanField(default=False)
    order=models.IntegerField(null=True, blank=True)
    option_type=models.CharField(max_length=12, choices=OPTION_TYPE_CHOICES)
    options=models.TextField(blank=True, editable=False, default='')

  def __unicode__(self):
      return self.question

