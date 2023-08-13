from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.shortcuts import redirect

from .models import Follow, Group, Post, User
from .forms import PostForm, CommentForm
from .utils import paginator

NUMBER_OF_POSTS: int = 10


def index(request):
    """Главная страница сайта."""
    posts = Post.objects.all()
    page_obj = paginator(request, posts, NUMBER_OF_POSTS)
    template = 'posts/index.html'
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    context.update(paginator(request, posts, NUMBER_OF_POSTS))
    return render(request, template, context)


def group_posts(request, slug):
    """Страница с постами, отфильтрованными по группам;
    view-функция принимает параметр slug из path().
    """
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    template = 'posts/group_list.html'
    page_obj = paginator(request, post_list, NUMBER_OF_POSTS)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    context.update(paginator(request, post_list, NUMBER_OF_POSTS))
    return render(request, template, context)


def profile(request, username):
    """Страница профиля пользователя."""
    author = get_object_or_404(User, username=username)
    profile_list = author.posts.all()
    all_posts = profile_list.count()
    following = Follow.objects.filter(
        author=author, user=request.user.id
    ).exists()
    page_obj = paginator(request, profile_list, NUMBER_OF_POSTS)
    context = {
        'page_obj': page_obj,
        'all_posts': all_posts,
        'author': author,
        'following': following,
    }
    context.update(paginator(request, profile_list, NUMBER_OF_POSTS))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница отдельного поста."""
    post = get_object_or_404(Post, pk=post_id)
    all_posts = post.author.posts.all().count()
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'all_posts': all_posts,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Страница создания поста."""
    template = 'posts/create_post.html'
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            files=request.FILES or None
        )
        if form.is_valid():
            form.save(commit=False).author = request.user
            form.save()
            user = request.user
            return redirect('posts:profile', user)
        return render(request, template, {'form': form})
    form = PostForm()
    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    """Страница редактирования поста."""
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, id=post_id)
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if request.user != post.author:
        return redirect('posts:post_detail', post_id)

    elif request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id)
        return render(request, template, {'form': form})

    context = {
        'form': form,
        'is_edit': is_edit,
        'post': post,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария к посту."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница с постами авторов, на которых
    подписан пользователь.
    """
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator(request, posts, NUMBER_OF_POSTS)
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    context.update(paginator(request, posts, NUMBER_OF_POSTS))
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписка на автора."""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Отписка от автора."""
    Follow.objects.filter(
        user=request.user, author__username=username
    ).delete()
    return redirect('posts:profile', username=username)
