from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, Post

User = get_user_model()


# Класс для создания нового поста
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {
            'text': 'Текст нового поста',
            'group': 'Группа, к которой будет относиться пост',
            'image': 'Картинка к посту',
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if data.isspace():
            raise forms.ValidationError(
                'Текст поста отсутствует',
                params={'data': data},
            )
        return data


# Класс для создания комментария к посту
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text', )
        help_texts = {
            'text': 'Текст комментария',
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if data.isspace():
            raise forms.ValidationError(
                'Текст комментария отсутствует',
                params={'data': data},
            )
        return data
