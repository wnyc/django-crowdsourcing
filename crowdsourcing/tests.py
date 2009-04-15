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
            fieldname="color",
            question="What is your favorite color?",
            order=1,
            option_type='char')
        self.survey.questions.create(
            fieldname="video",
            question="Add a video",
            order=2,
            option_type="video")
        self.survey.questions.create(
            fieldname='email',
            question='Your email',
            order=3,
            option_type="email")

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

    def testAnswer1(self):
        answer=self.submission.answer_set.create(
            question=self.survey.questions.all()[0])
        answer.value='chartreuse'
        answer.save()
        self.assertEquals(answer.text_answer, 'chartreuse')
        self.assertEquals(self.submission.color, 'chartreuse')

    def testAnswer2(self):
        q=self.survey.questions.get(fieldname='video')
        answer=self.submission.answer_set.create(
            question=q)
        vid='http://www.youtube.com/watch?v=lHVahvnK3Uk'
        answer.value=vid
        answer.save()
        self.assertEquals(answer.text_answer, vid)
        self.assertEquals(self.submission.video, vid)

    def testAnswer3(self):
        q=self.survey.questions.get(fieldname='email')
        answer=self.submission.answer_set.create(
            question=q)
        e='grappelli@fudgesickle.com'
        answer.value=e
        answer.save()
        self.assertEquals(answer.text_answer, e)
        self.assertEquals(self.submission.email, e)        
        
