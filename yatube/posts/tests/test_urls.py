# posts/tests/test_urls.py
from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Post, Group

User = get_user_model()


class PostURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованного клиента
        self.user = User.objects.create_user(username='Somebody')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # создаем авторизованного автора поста
        self.author_client = Client()
        self.author = PostURLTest.user
        self.author_client.force_login(self.author)

    # Проверка общедоступных страниц
    def test_public_urls(self):
        """Страницы доступны любому пользователю."""
        url_status_names = {
            '/': HTTPStatus.OK,
            '/group/slug/': HTTPStatus.OK,
            reverse(
                'posts:profile',
                args=(self.user.username,)
            ): HTTPStatus.OK,
            reverse('posts:post_detail', args=(self.post.id,)): HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for url, status in url_status_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status)

    # Проверяем доступность страниц для авторизованного пользователя
    def test_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    """
    # Проверяем доступность страниц для авторизованного пользователя
    def test_add_comment_url_exists_at_desired_location(self):
        Страница /posts/post_id/comment/
        доступна авторизованному пользователю.
        response = self.authorized_client.get(
            reverse('posts:add_comment', args=(self.post.id,))
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
    """

    # Проверяем доступность страниц для автора поста
    def test_edit_url_exists_at_desired_location(self):
        """Страница /posts/post_id/edit/ доступна автору поста."""
        response = self.author_client.get(
            reverse('posts:post_edit', args=(self.post.id,))
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем редиректы для неавторизованного пользователя
    def test_create_url_redirect_anonymous_on_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    # Проверяем редиректы для неавторизованного пользователя
    def test_add_comment_url_redirect_anonymous_on_login(self):
        """Страница по адресу /posts/post_id/comment/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get(
            reverse('posts:add_comment', args=(self.post.id,)),
            follow=True
        )
        self.assertRedirects(
            response, (f'/auth/login/?next=/posts/{self.post.id}/comment/')
        )

    def test_edit_url_redirect_anonymous_on_login(self):
        """Страница по адресу /posts/post_id/edit/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get(
            reverse('posts:post_edit', args=(self.post.id,)),
            follow=True
        )
        self.assertRedirects(
            response, (f'/auth/login/?next=/posts/{self.post.id}/edit/')
        )

    # Проверяем редиректы для не автора поста
    def test_edit_url_redirect_not_author_on_post_id(self):
        """Страница по адресу /posts/post_id/edit/ перенаправит не автора
        поста на страницу просмотра поста.
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=(self.post.id,)),
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=(self.post.id,))
        )

    # Проверка вызываемых шаблонов анонимным пользователем для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/slug/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertTemplateUsed(response, template)
