"""
run these tests with nose.
"""

from __future__ import absolute_import
import unittest

from .models import Survey, Question, Answer, Submission

class SurveyTestCase(unittest.TestCase):
    def setUp(self):
        self.survey=Survey.objects.create(
            title="Test Survey",
            slug="test-survey",
            is_published=True)
        self.survey.questions.create(
            fieldname="q1",
            question="What is your favorite color?",
            order=1,
            option_type='char')

    def tearDown(self):
        self.survey.delete()
        
    def testLive1(self):
        self.assertEquals(self.survey,
                          Survey.live.get(slug=self.survey.slug))
            
    def testLive2(self):
        self.survey.is_published=False
        self.survey.save()
        def getit():
            return Survey.live.get(slug=self.survey.slug)
        self.assertRaises(Survey.DoesNotExist, getit)
            

class SubmissionTestCase(SurveyTestCase):

    def setUp(self):
        super(SubmissionTestCase, self).setUp()
        self.submission=self.survey.submission_set.create(
            ip_address='127.0.0.1',
            session_key='X' * 40)

    def testAnswer(self):
        answer=self.submission.answer_set.create(
            question=self.survey.questions.all()[0])
        answer.value='chartreuse'
        answer.save()
        self.assertEquals(answer.text_answer, 'chartreuse')
            
        
