from django import forms
from .models import CourseReview


class CourseReviewForm(forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ['rating', 'title', 'review_text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Summarize your review (optional)'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Share your learning experience...',
                'rows': 5
            }),
        }
        labels = {
            'rating': 'Your Rating',
            'title': 'Review Title',
            'review_text': 'Your Review',
        }
