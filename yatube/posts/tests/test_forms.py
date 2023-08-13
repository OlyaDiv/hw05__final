import shutil
import tempfile
from django.contrib.auth import get_user_model
from django .core.files.uploadedfile import SimpleUploadedFile
from http import HTTPStatus

from ..forms import PostForm
from ..models import Comment, Group, Post
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# временная папка TEMP_MEDIA_ROOT для сохранения media-файлов
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_2',
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            author=cls.user,
            post=cls.post,
        )
        # Создаем форму, если нужна проверка атрибутов
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        # Создаем авторизованного клиента
        self.user = User.objects.create_user(username='Somebody')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # создаем авторизованного автора поста
        self.author_client = Client()
        self.author = PostCreateFormTests.user
        self.author_client.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        # Отправляем POST-запрос
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.post.author,))
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем, что создалась верная запись
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.post.author,
                image=f'posts/{uploaded.name}',
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data_after_edit = {
            'text': 'Тестовый пост 2',
            'group': self.group2.id,
        }
        response_after_edit = self.author_client.post(
            reverse('posts:post_edit', args=(self.post.id,)),
            data=form_data_after_edit,
            follow=True
        )
        self.assertRedirects(response_after_edit, reverse(
            'posts:post_detail', args=(self.post.id,))
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response_after_edit.status_code, HTTPStatus.OK)
        self.assertTrue(
            Post.objects.filter(
                text=form_data_after_edit['text'],
                group=form_data_after_edit['group'],
                author=self.post.author,
            ).exists()
        )
        self.assertNotEqual(self.post.text, form_data_after_edit['text'])
        self.assertNotEqual(self.post.group.id, form_data_after_edit['group'])

    def test_create_comment(self):
        """Валидная форма создает комментарий."""
        comments_count = Comment.objects.filter(post=self.post.id).count()
        form_data = {
            'text': 'Тестовый комментарий',
            'post': self.post.id,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.id,))
        )
        # Проверяем, увеличилось ли число комментариев
        self.assertEqual(
            self.post.comments.all().count(),
            comments_count + 1
        )
        # Проверяем, что создался верный комментарий
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                post=form_data['post'],
                author=self.post.author,
            ).exists()
        )
