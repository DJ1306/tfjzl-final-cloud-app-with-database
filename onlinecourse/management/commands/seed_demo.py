"""Create the course and mock exam specified by the lab."""
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from onlinecourse.models import Course, Instructor, Lesson, Question, Choice, Enrollment


class Command(BaseCommand):
    help = 'Create the Learning Django example course and mock exam.'

    def handle(self, *args, **options):
        User = get_user_model()
        admin = User.objects.filter(username='admin').first()
        if admin is None:
            password = os.environ.get('DEMO_ADMIN_PASSWORD')
            if not password:
                raise CommandError('Set DEMO_ADMIN_PASSWORD before creating the demo administrator.')
            admin = User.objects.create_superuser('admin', '', password)
        instructor, _ = Instructor.objects.get_or_create(user=admin, defaults={'total_learners': 1})
        course, _ = Course.objects.get_or_create(name='Learning Django', defaults={
            'description': 'Django is a fully featured server-side web framework, written in Python.',
            'pub_date': now().date(), 'image': 'course_images/django.png', 'total_enrollment': 1,
        })
        course.instructors.add(instructor)
        Lesson.objects.get_or_create(course=course, order=0, defaults={
            'title': 'What is Django',
            'content': 'Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design.',
        })
        question, _ = Question.objects.get_or_create(course=course, content='Is Django a Python framework', defaults={'grade': 100})
        Choice.objects.get_or_create(question=question, content='Yes', defaults={'is_correct': True})
        Choice.objects.get_or_create(question=question, content='No', defaults={'is_correct': False})
        Enrollment.objects.get_or_create(user=admin, course=course)
        self.stdout.write(self.style.SUCCESS(f'Learning Django is ready. Course ID: {course.id}'))
