from django.contrib import admin
from .models import ForumCategory, Topic, Post, PostVote


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "order")
    list_filter = ("course",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "is_pinned", "is_locked",
                    "view_count", "last_activity")
    list_filter = ("is_pinned", "is_locked", "category")
    search_fields = ("title", "author__username")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("topic", "author", "is_solution", "is_flagged",
                    "is_hidden", "upvotes", "created")
    list_filter = ("is_flagged", "is_hidden", "is_solution")
    search_fields = ("body", "author__username")
    actions = ["hide_posts", "unhide_posts"]

    @admin.action(description="Hide selected posts")
    def hide_posts(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Unhide selected posts")
    def unhide_posts(self, request, queryset):
        queryset.update(is_hidden=False)


admin.site.register(PostVote)
