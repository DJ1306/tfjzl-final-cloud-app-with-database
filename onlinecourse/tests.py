"""Exercise grading, answer validation and submission ownership."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Course, Enrollment, Question, Choice, Submission


class ExamTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('learner', password='test-only-password')
        self.course = Course.objects.create(name='Test course')
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.question = Question.objects.create(course=self.course, content='Select both correct answers', grade=100)
        self.first = Choice.objects.create(question=self.question, content='Correct 1', is_correct=True)
        self.second = Choice.objects.create(question=self.question, content='Correct 2', is_correct=True)
        self.wrong = Choice.objects.create(question=self.question, content='Wrong')
        self.client.force_login(self.user)
        self.url = reverse('onlinecourse:submit', args=[self.course.id])

    def test_exact_multiple_selection_passes(self):
        response = self.client.post(self.url, {'choice_1': [self.first.id, self.second.id]}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['passed'])
        self.assertEqual(response.context['grade'], 100)
        self.assertContains(response, 'Congratulations')
        self.assertEqual(Submission.objects.get().choices.count(), 2)

    def test_selecting_every_answer_does_not_pass(self):
        response = self.client.post(self.url, {'choice_1': [self.first.id, self.second.id, self.wrong.id]}, follow=True)
        self.assertFalse(response.context['passed'])
        self.assertEqual(response.context['grade'], 0)

    def test_partial_answer_does_not_pass(self):
        response = self.client.post(self.url, {'choice_1': self.first.id}, follow=True)
        self.assertEqual(response.context['grade'], 0)

    def test_empty_submission_is_recorded_as_failed(self):
        response = self.client.post(self.url, {}, follow=True)
        self.assertFalse(response.context['passed'])
        self.assertEqual(Submission.objects.count(), 1)

    def test_other_course_answer_is_rejected(self):
        other = Course.objects.create(name='Other course')
        question = Question.objects.create(course=other, content='Other question')
        choice = Choice.objects.create(question=question, content='Other answer', is_correct=True)
        self.assertEqual(self.client.post(self.url, {'choice_1': choice.id}).status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_identifier_is_rejected(self):
        self.assertEqual(self.client.post(self.url, {'choice_1': 'invalid'}).status_code, 400)

    def test_get_cannot_submit(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(Submission.objects.count(), 0)

    def test_another_learner_cannot_read_result(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        other = get_user_model().objects.create_user('other')
        self.client.force_login(other)
        result_url = reverse('onlinecourse:show_exam_result', args=[self.course.id, submission.id])
        self.assertEqual(self.client.get(result_url).status_code, 404)

    def test_unauthenticated_submission_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {}).status_code, 302)

    def test_course_page_contains_lessons_and_exam(self):
        response = self.client.get(reverse('onlinecourse:course_details', args=[self.course.id]))
        self.assertContains(response, 'Start Exam')
        self.assertContains(response, 'Select both correct answers')
