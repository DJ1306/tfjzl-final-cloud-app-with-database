"""Exercise grading, answer validation and submission ownership."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from .models import Course, Enrollment, Question, Choice, Submission


class ExamTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('learner', password='test-only-password')
        self.course = Course.objects.create(name='Test course')
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.question = Question.objects.create(course=self.course, question_text='Select both correct answers', grade=100)
        self.first = Choice.objects.create(question=self.question, choice_text='Correct 1', is_correct=True)
        self.second = Choice.objects.create(question=self.question, choice_text='Correct 2', is_correct=True)
        self.wrong = Choice.objects.create(question=self.question, choice_text='Wrong')
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
        question = Question.objects.create(course=other, question_text='Other question')
        choice = Choice.objects.create(question=question, choice_text='Other answer', is_correct=True)
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
        self.assertContains(response, 'Correct 1')

    def test_default_weight_question_preserves_weighted_grading_and_feedback(self):
        question = Question.objects.create(course=self.course, question_text='One point question')
        choice = Choice.objects.create(question=question, choice_text='One point answer', is_correct=True)
        response = self.client.post(self.url, {f'choice_{question.id}': choice.id}, follow=True)
        self.assertEqual(response.context['total_score'], 101)
        self.assertEqual(response.context['earned_score'], 1)
        self.assertEqual(response.context['grade'], 0.99)
        self.assertContains(response, 'One point question')
        self.assertContains(response, 'One point answer')
        self.assertIn(self.user.username, str(Submission.objects.get()))


class AssessmentMigrationTests(TransactionTestCase):
    def test_field_renames_preserve_existing_exam_and_submission(self):
        previous = [('onlinecourse', '0001_initial')]
        current = [('onlinecourse', '0002_assessment_rubric_fields')]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        old_apps = executor.loader.project_state(previous).apps
        try:
            user = old_apps.get_model('auth', 'User').objects.create(username='existing-learner')
            course = old_apps.get_model('onlinecourse', 'Course').objects.create(name='Existing course')
            enrollment = old_apps.get_model('onlinecourse', 'Enrollment').objects.create(user=user, course=course)
            question = old_apps.get_model('onlinecourse', 'Question').objects.create(course=course, content='Existing question', grade=100)
            choice = old_apps.get_model('onlinecourse', 'Choice').objects.create(question=question, content='Existing answer', is_correct=True)
            submission = old_apps.get_model('onlinecourse', 'Submission').objects.create(enrollment=enrollment)
            submission.choices.add(choice)
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            new_apps = executor.loader.project_state(current).apps
            saved_question = new_apps.get_model('onlinecourse', 'Question').objects.get(pk=question.pk)
            saved_choice = new_apps.get_model('onlinecourse', 'Choice').objects.get(pk=choice.pk)
            saved_submission = new_apps.get_model('onlinecourse', 'Submission').objects.get(pk=submission.pk)
            self.assertEqual(saved_question.question_text, 'Existing question')
            self.assertEqual(saved_question.grade, 100)
            self.assertEqual(saved_choice.choice_text, 'Existing answer')
            self.assertEqual(list(saved_submission.choices.values_list('pk', flat=True)), [choice.pk])
        finally:
            MigrationExecutor(connection).migrate(current)
