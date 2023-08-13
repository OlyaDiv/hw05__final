# from tokenize import group
# from email.mime import image
import shutil
import tempfile
from django.contrib.auth import get_user_model
from django .core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.urls import reverse
from django import forms
from django.conf import settings

from ..models import Follow, Group, Post

User = get_user_model()

POSTS_ON_PAGE = 16
POSTS_ON_FIRST_PAGE = 10
POSTS_ON_SECOND_PAGE = 5

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованного клиента
        # self.user = User.objects.create_user(username='Somebody')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # создаем авторизованного автора поста
        self.author_client = Client()
        self.author = PostViewTest.user
        self.author_client.force_login(self.author)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "reverse(name): имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                args=(self.group.slug,)
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                args=(self.user.username,)
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                args=(self.post.id,)
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                args=(self.post.id,)
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка словаря context страницы index
    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.id, self.post.id)
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.image, self.post.image)

    # Проверка словаря context страницы group_list
    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.id, self.post.id)
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.image, self.post.image)

    # Проверка словаря context страницы profile
    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.id, self.post.id)
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.image, self.post.image)

    # Проверка словаря context страницы post_detail
    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.id,))
        )
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)

    # Проверка словаря context страницы create_post (в нём передаётся форма)
    def test_create_post_show_correct_context(self):
        """На странице create_post сформирована
        правильная форма создания поста.
        """
        response = self.authorized_client.get(reverse('posts:post_create'))
        # Словарь ожидаемых типов полей формы:
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        # Проверяем, что типы полей формы соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # Проверка словаря context страницы create_post (в нём передаётся форма)
    def test_create_post_show_correct_context(self):
        """На странице create_post сформирована
        правильная форма редактирования поста.
        """
        response = self.author_client.get(
            reverse('posts:post_edit', args=(self.post.id,))
        )
        # Словарь ожидаемых типов полей формы:
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        # Проверяем, что типы полей формы соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # Дополнительная проверка при создании поста с группой
    def test_post_with_group_show_correct(self):
        """Если при создании поста указать группу,
        он появится на страницах index, group_list, profile.
        """
        group = Group.objects.create(
            title='Тестовая группа 1',
            slug='test_slug_1',
            description='Тестовое описание 1',
        )
        group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_2',
            description='Тестовое описание 2',
        )
        post = Post.objects.create(
            text='Тестовый пост с группой',
            author=self.user,
            group=group,
        )
        responses = {
            'index': self.author_client.get(reverse('posts:index')),
            'group_list': self.author_client.get(
                reverse('posts:group_list', args=(group.slug,))
            ),
            'profile': self.author_client.get(
                reverse('posts:profile', args=(post.author,))
            ),
        }
        for response in responses.values():
            first_object = response.context['page_obj'][0]
            self.assertEqual(first_object.text, post.text)
            self.assertEqual(first_object.author, post.author)
            self.assertEqual(first_object.group.id, group.id)
            self.assertNotEqual(first_object.group.id, group2.id)

    # Проверка кэширования главной страницы
    def test_cache_index_page(self):
        """Тест кэширования главной страницы."""
        cache.clear()
        post_2 = Post.objects.create(
            text='Тестируем кэш',
            author=self.user,
        )
        first_response = self.guest_client.get(reverse('posts:index'))
        first_content = first_response.content
        object_before_delete = first_response.context['page_obj'][0]
        self.assertEqual(object_before_delete.text, post_2.text)
        post_2.delete()
        second_response = self.guest_client.get(reverse('posts:index'))
        second_content = second_response.content
        self.assertEqual(first_content, second_content)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        for i in range(2, POSTS_ON_PAGE):
            Post.objects.create(
                text=f'Тестовый пост {i}',
                group=cls.group,
                author=cls.user,
            )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='Somebody')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем паджинатор
    def test_paginator(self):
        pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', args=(self.group.slug,)),
            reverse('posts:profile', args=(self.post.author,)),
        }
        for page in pages_names:
            response_first_page = self.authorized_client.get(page)
            response_second_page = self.authorized_client.get(page + '?page=2')
            posts_on_first_page = len(response_first_page.context['page_obj'])
            posts_on_second_page = len(
                response_second_page.context['page_obj']
            )
            self.assertEqual(posts_on_first_page, POSTS_ON_FIRST_PAGE)
            self.assertEqual(posts_on_second_page, POSTS_ON_SECOND_PAGE)


class FollowViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user_follower = User.objects.create_user(username='follower')
        cls.user_not_follower = User.objects.create_user(username='somebody')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client_follower = Client()
        self.authorized_client_follower.force_login(self.user_follower)
        self.authorized_client_not_follower = Client()
        self.authorized_client_not_follower.force_login(self.user_not_follower)

    # Проверяем возможность подписки и отписки от авторов
    def test_follow_and_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок.
        """
        Follow.objects.create(user=self.user_follower, author=self.author)
        self.assertTrue(Follow.objects.filter(
            user=self.user_follower, author=self.author).exists()
        )
        Follow.objects.filter(
            user=self.user_follower, author=self.author
        ).delete()
        self.assertFalse(Follow.objects.filter(
            user=self.user_follower, author=self.author).exists()
        )

    # Проверка появления поста в ленте подписчика
    def test_post_show_correct_for_follower(self):
        """Новая запись пользователя появляется в ленте тех, кто подписан
        на него и не появляется в ленте тех, кто не подписан.
        """
        Follow.objects.create(user=self.user_follower, author=self.author)
        response_before_post = self.authorized_client_follower.get(
            reverse('posts:follow_index')
        )
        response_before_not_follower = self.authorized_client_not_follower.get(
            reverse('posts:follow_index')
        )
        post = Post.objects.create(author=self.author, text='Новый пост')
        response_after_post = self.authorized_client_follower.get(
            reverse('posts:follow_index')
        )
        response_after_not_follower = self.authorized_client_not_follower.get(
            reverse('posts:follow_index')
        )
        self.assertNotEqual(
            response_before_post.content,
            response_after_post.content
        )
        self.assertEqual(
            response_before_not_follower.content,
            response_after_not_follower.content
        )
        new_posts = response_after_post.context['page_obj']
        self.assertIn(post, new_posts)
