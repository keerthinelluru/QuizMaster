from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .forms import SignupForm
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Quiz, UserSubmission,Question
from .models import Subject
from django.contrib import messages
from django import forms
from django.http import Http404
from .models import UserSubmission,Notification
from django.db.models import Avg, Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import UserProfile
from django.db.models import   F, FloatField, ExpressionWrapper
from io import BytesIO
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import BookmarkedQuestion
from reportlab.lib import colors


def home(request):
    return render(request, 'accounts/home.html')


# SIGNUP VIEW (COMMON)
def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])

            role = form.cleaned_data.get('role')
            if role == 'admin':
                user.is_staff = True
            else:
                user.is_staff = False

            user.save()
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')  # This must match your URL name
            else:
                return redirect('user_dashboard')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'accounts/login.html')


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('home')

# USER DASHBOARD
@login_required
@user_passes_test(lambda u: not u.is_staff)
def user_dashboard(request):
    subjects = Subject.objects.prefetch_related('quiz_set').all()
    submissions = UserSubmission.objects.filter(user=request.user)


    subject_progress = []

    for subject in subjects:
       quizzes = subject.quiz_set.all()
       total = quizzes.count()
       attempted = submissions.filter(quiz__in=quizzes).values('quiz').distinct().count()
       percent = int((attempted / total) * 100) if total > 0 else 0

       subject_progress.append({
        'subject': subject,
        'quizzes': quizzes,
        'attempted': attempted,
        'total': total,
        'percent': percent,
    })

    total_attempts = submissions.count()
    avg_score = submissions.aggregate(avg=Avg('score'))['avg']
    avg_score = round(avg_score or 0, 2)

    return render(request, 'accounts/user_dashboard.html', {
    'subject_progress': subject_progress,
    'total_attempts': total_attempts,
    'avg_score': avg_score
})
   


# ADMIN DASHBOARD
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    total_users = User.objects.filter(is_staff=False).count()
    total_quizzes = Quiz.objects.count()
    total_attempts = UserSubmission.objects.count()
    return render(request, 'accounts/admin_dashboard.html', {
    'total_users': total_users,
    'total_quizzes': total_quizzes,
    'total_attempts': total_attempts
})



def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])

            # Set is_staff if checkbox selected
            if form.cleaned_data.get('role') == 'admin':
              user.is_staff = True
            else:
              user.is_staff = False

            user.save()
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})

def is_admin(user):
    return user.is_staff


@login_required
@user_passes_test(lambda u: u.is_staff)
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, 'accounts/subject_list.html', {'subjects': subjects})

@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_list(request):
    return render(request, 'accounts/quiz_list.html')

@login_required
@user_passes_test(lambda u: u.is_staff)
def question_list(request):
    return render(request, 'accounts/question_list.html')
@login_required
@user_passes_test(lambda u: u.is_staff)
def view_submissions(request):
    return render(request, 'accounts/view_submissions.html')

@login_required
@user_passes_test(lambda u: u.is_staff)
def subject_create(request):
    if request.method == 'POST':
        print("POST request received:", request.POST)
        name = request.POST.get('name')
        if name:
            Subject.objects.create(name=name)
            messages.success(request, 'Subject created successfully.')
            return redirect('subject_list')
    return render(request, 'accounts/subject_form.html', {'form_type': 'create'})

@login_required
@user_passes_test(lambda u: u.is_staff)
def subject_edit(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            subject.name = name
            subject.save()
            messages.success(request, 'Subject updated successfully.')
            return redirect('subject_list')

    return render(request, 'accounts/subject_form.html', {
        'form_type': 'edit',
        'subject': subject
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def subject_delete(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject deleted successfully.')
        return redirect('subject_list')

    return render(request, 'accounts/subject_confirm_delete.html', {'subject': subject})

@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_create(request):
    subjects = Subject.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        subject_id = request.POST.get('subject')

        if title and subject_id:
            subject = get_object_or_404(Subject, id=subject_id)
            Quiz.objects.create(title=title, subject=subject)
            messages.success(request, "Quiz created successfully.")
            return redirect('quiz_list')

    return render(request, 'accounts/quiz_form.html', {'subjects': subjects, 'form_type': 'create'})



@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_list(request):
    subjects = Subject.objects.prefetch_related('quiz_set').all()
    return render(request, 'accounts/quiz_list.html', {'subjects': subjects})


@login_required
@user_passes_test(lambda u: u.is_staff)
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        print("POST DATA:", request.POST)
        text = request.POST.get('text')
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')

        if all([text, option1, option2, option3, option4, correct_answer]):
            # ✅ Save to a variable before printing
            question = Question.objects.create(
                quiz=quiz,
                text=text,
                option1=option1,
                option2=option2,
                option3=option3,
                option4=option4,
                correct_answer=correct_answer
            )
            print("✅ Question Saved:", question)
            messages.success(request, "Question added successfully.")
            return redirect('quiz_list')
        else:
            messages.error(request, "All fields are required.")

    return render(request, 'accounts/add_question.html', {'quiz': quiz})

@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    return render(request, 'accounts/quiz_questions.html', {
        'quiz': quiz,
        'questions': questions
}) 

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_question(request,  quiz_id, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.text = request.POST.get('text')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.save()
        messages.success(request, "Question updated successfully.")
        return redirect('quiz_questions', quiz_id=question.quiz.id)

    return render(request, 'accounts/edit_question.html', {'question': question})

@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_question(request,  quiz_id, question_id):
    question = get_object_or_404(Question, id=question_id)
    quiz_id = question.quiz.id
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted successfully.")
        return redirect('quiz_questions', quiz_id=quiz_id)
    return render(request, 'accounts/delete_question_confirm.html', {'question': question})

@login_required
@user_passes_test(lambda u: not u.is_staff)
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if not questions.exists():
        messages.error(request, "This quiz has no questions.")
        return redirect('user_dashboard')

    # Initialize session
    request.session['quiz_id'] = quiz.id
    request.session['question_index'] = 0
    request.session['score'] = 0
    request.session['answers'] = {}

    return redirect('quiz_question')


@login_required
@user_passes_test(lambda u: not u.is_staff)
def quiz_question(request):
    from .models import BookmarkedQuestion  # make sure this is imported

    quiz_id = request.session.get('quiz_id')
    index = request.session.get('question_index', 0)

    if quiz_id is None:
        messages.error(request, "Session expired. Please start the quiz again.")
        return redirect('user_dashboard')

    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = list(quiz.questions.all())

    if index >= len(questions):
        return redirect('quiz_result')

    question = questions[index]

    if request.method == 'POST':
        selected = request.POST.get('answer')
        answers = request.session.get('answers', {})

        # Bookmark check first
        if 'bookmark' in request.POST:
            BookmarkedQuestion.objects.get_or_create(user=request.user, question=question)
            messages.success(request, "🔖 Question bookmarked.")
            return redirect('quiz_question')

        # Save selected answer
        answers[str(question.id)] = selected
        request.session['answers'] = answers

        if selected == question.correct_answer:
            request.session['score'] += 1

        request.session['question_index'] += 1
        return redirect('quiz_question')

    return render(request, 'accounts/quiz_question.html', {
        'question': question,
        'quiz': quiz,
        'index': index + 1,
        'total': len(questions)
    })


@login_required
@user_passes_test(lambda u: not u.is_staff)
def quiz_result(request):
    score = request.session.get('score', 0)
    answers = request.session.get('answers', {})
    quiz_id = request.session.get('quiz_id')

    quiz = get_object_or_404(Quiz, id=quiz_id)
    total_questions = quiz.questions.count()

    # Save attempt
    UserSubmission.objects.create(
        user=request.user,
        quiz=quiz,
        score=score,
        total=total_questions
    )

    # Clear session
    for key in ['score', 'answers', 'question_index', 'quiz_id']:
        request.session.pop(key, None)

    # ✅ Determine if eligible for certificate
    show_certificate = (score / total_questions) >= 0.8

    return render(request, 'accounts/quiz_result.html', {
        'quiz': quiz,
        'score': score,
        'total': total_questions,
        'show_certificate': show_certificate  # <-- send to template
    })


@login_required
@user_passes_test(lambda u: not u.is_staff)
def user_history(request):
    submissions = UserSubmission.objects.filter(user=request.user).select_related('quiz__subject').order_by('-submitted_at')
    return render(request, 'accounts/user_history.html', {
        'submissions': submissions
    })
@login_required
@user_passes_test(lambda u: u.is_staff)
def view_all_submissions(request):
    submissions = UserSubmission.objects.select_related('user', 'quiz__subject').order_by('-submitted_at')
    return render(request, 'accounts/view_all_submissions.html', {
        'submissions': submissions
    })



@login_required
def user_performance_graph(request):
    subjects = Subject.objects.all()
    performance_data = []

    for subject in subjects:
      user_quizzes = Quiz.objects.filter(subject=subject)
      submissions = UserSubmission.objects.filter(user=request.user, quiz__in=user_quizzes)

      avg_score = submissions.aggregate(avg=Avg('score'))['avg']
      total_attempts = submissions.count()

      performance_data.append({
          'subject': subject.name,
           'avg_score': round(avg_score or 0, 2),
            'attempts': total_attempts
    })

    return render(request, 'accounts/performance_graph.html', {'performance_data': performance_data})

@login_required
@user_passes_test(lambda u: u.is_staff)
def send_notification(request):
    subjects = Subject.objects.all()

    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        title = request.POST.get('title')
        message = request.POST.get('message')
        link = request.POST.get('link')

        if subject_id and title and message:
            subject = get_object_or_404(Subject, id=subject_id)
            Notification.objects.create(
                subject=subject,
                title=title,
                message=message,
                link=link
            )
            messages.success(request, 'Notification sent successfully.')
            return redirect('send_notification')

    return render(request, 'accounts/send_notification.html', {'subjects': subjects})

@login_required
@user_passes_test(lambda u: not u.is_staff)
def user_notifications(request):
    from .models import Notification
    notifications = Notification.objects.all().order_by('-created_at')
    return render(request, 'accounts/user_notifications.html', {
      'notifications': notifications
})

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
      UserProfile.objects.create(user=instance)


@login_required
@user_passes_test(lambda u: not u.is_staff)
def leaderboard_view(request):
  from django.contrib.auth.models import User
  from .models import UserSubmission


# Annotate users with total score and total questions attempted
  users = User.objects.filter(is_staff=False).annotate(
      total_score=Sum('usersubmission__score'),
      total_questions=Sum('usersubmission__total'),
      total_attempts=Count('usersubmission'),
    ).annotate(
        accuracy=ExpressionWrapper(
          100 * F('total_score') / F('total_questions'),
           output_field=FloatField()
    )
).order_by('-accuracy')  # Sort by accuracy

  return render(request, 'accounts/leaderboard.html', {'users': users})




@login_required
@user_passes_test(lambda u: not u.is_staff)
def generate_certificate(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # ✅ Get the latest submission instead of get()
    submission = UserSubmission.objects.filter(user=request.user, quiz=quiz).latest('submitted_at')

    percentage = (submission.score / submission.total) * 100
    if percentage < 80:
        return HttpResponse("❌ You must score at least 80% to download a certificate.")

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4 
    # 🟩 Draw Border  
    p.setStrokeColorRGB(0.2, 0.2, 0.2)  
    p.setLineWidth(5)  
    p.rect(40, 40, width - 80, height - 80)  

# 🏅 Certificate Title  
    p.setFont("Helvetica-Bold", 30)  
    p.setFillColor(colors.darkblue)  
    p.drawCentredString(width / 2, height - 100, "Certificate of Achievement")  

# 👤 Presented to  
    p.setFont("Helvetica", 18)  
    p.setFillColor(colors.black)  
    p.drawCentredString(width / 2, height - 160, f"Presented to")  

    p.setFont("Helvetica-Bold", 22)  
    p.setFillColor(colors.darkgreen)  
    p.drawCentredString(width / 2, height - 190, request.user.username)  

# 📝 Quiz + Score  
    p.setFont("Helvetica", 16)  
    p.setFillColor(colors.black)  
    p.drawCentredString(width / 2, height - 230, f"For scoring {submission.score}/{submission.total} in “{quiz.title}”")  
    p.drawCentredString(width / 2, height - 260, f"Date: {submission.submitted_at.strftime('%Y-%m-%d')}")  

# ✨ Footer  
    p.setFont("Helvetica-Oblique", 12)  
    p.setFillColor(colors.grey)  
    p.drawCentredString(width / 2, 80, "This certificate is awarded for outstanding performance.")  

# 🖋 Optional Signature  
    p.setFont("Helvetica", 12)  
    p.setFillColor(colors.black)  
    p.drawString(width - 180, 60, "Signature")  
    p.line(width - 250, 55, width - 100, 55)  

# 🖨 Finalize  
    p.showPage()  
    p.save()  
    buffer.seek(0)  
    return FileResponse(buffer, as_attachment=True, filename='certificate.pdf')



@login_required
@user_passes_test(lambda u: not u.is_staff)
def view_bookmarked_questions(request):
    bookmarks = BookmarkedQuestion.objects.filter(user=request.user).select_related('question__quiz')
    return render(request, 'accounts/bookmarked_questions.html', {
  'bookmarks': bookmarks
})