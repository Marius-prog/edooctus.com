from django.urls import path, include
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

from shared.permissions import IsOwnerOrReadOnly
from .models import ForumCategory, Topic, Post, PostVote

app_name = "forum"


class CategorySer(serializers.ModelSerializer):
    class Meta:
        model = ForumCategory
        fields = ["id", "course", "name", "slug", "description", "order"]


class TopicSer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "category", "author", "title", "slug",
                  "is_pinned", "is_locked", "view_count", "created", "last_activity"]
        read_only_fields = ["author", "view_count", "is_pinned", "is_locked",
                            "created", "last_activity"]


class PostSer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "topic", "parent", "author", "body", "is_solution",
                  "upvotes", "created", "edited_at"]
        read_only_fields = ["author", "upvotes", "created", "edited_at"]


class CategoryVS(viewsets.ReadOnlyModelViewSet):
    queryset = ForumCategory.objects.all()
    serializer_class = CategorySer
    permission_classes = [permissions.IsAuthenticated]


class TopicVS(viewsets.ModelViewSet):
    queryset = Topic.objects.select_related("category", "author")
    serializer_class = TopicSer
    permission_classes = [permissions.IsAuthenticated]
    owner_field = "author"

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostVS(viewsets.ModelViewSet):
    queryset = Post.objects.filter(is_hidden=False).select_related("topic", "author")
    serializer_class = PostSer
    permission_classes = [permissions.IsAuthenticated]
    owner_field = "author"

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def upvote(self, request, pk=None):
        post = self.get_object()
        _, created = PostVote.objects.get_or_create(post=post, user=request.user)
        if created:
            Post.objects.filter(pk=post.pk).update(upvotes=F("upvotes") + 1)
            post.refresh_from_db(fields=["upvotes"])
        return Response({"upvotes": post.upvotes})

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        post = self.get_object()
        post.is_flagged = True
        post.flag_reason = request.data.get("reason", "")[:200]
        post.save(update_fields=["is_flagged", "flag_reason"])
        return Response({"detail": "Flagged."}, status=status.HTTP_202_ACCEPTED)


class TopicListView(LoginRequiredMixin, ListView):
    model = Topic
    template_name = "forum/topic_list.html"


class TopicDetailView(LoginRequiredMixin, DetailView):
    model = Topic
    template_name = "forum/topic_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        Topic.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
        return obj


router = DefaultRouter()
router.register(r"categories", CategoryVS, basename="category")
router.register(r"topics", TopicVS, basename="topic")
router.register(r"posts", PostVS, basename="post")

urlpatterns = [
    path("", TopicListView.as_view(), name="list"),
    path("topic/<int:pk>/", TopicDetailView.as_view(), name="topic"),
    path("api/", include(router.urls)),
]
