
import graphene
import graphql_jwt
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from graphql_jwt.shortcuts import create_refresh_token, get_token

from feeds.models import Source, Post
from feeds.utils import update_feeds, read_feed


class UserType(DjangoObjectType):
    class Meta:
        model = get_user_model()

class SourceType(DjangoObjectType):
    class Meta:
        model = Source

class PostType(DjangoObjectType):
    class Meta:
        model = Post

class SourceInput(graphene.InputObjectType):
    feed_url = graphene.String()

class AddSource(graphene.Mutation):
    source = graphene.Field(SourceType)
    ok = graphene.Boolean()

    class Arguments:
        input = SourceInput(required=True)    

    def mutate(self, info, input=None):
        ok = True
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Not logged in!")

        source = Source.objects.create(user=user, feed_url=input.feed_url)
        read_feed(source_feed=source)
        return AddSource(ok=ok, source=source)


class RemoveSourceInput(graphene.InputObjectType):
    id = graphene.ID()

class RemoveSource(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        input = RemoveSourceInput(required=True)    

    def mutate(self, info, input=None):
        ok = True
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Not logged in!")

        source = Source.objects.get(id=input.id)
        if source.user != user:
            raise Exception("Not authorized!")

        source.delete()
        return RemoveSource(ok=ok)


class ReadInput(graphene.InputObjectType):
    id = graphene.ID()

class Read(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        input = ReadInput(required=True)    

    def mutate(self, info, input=None):
        ok = True
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Not logged in!")

        post = Post.objects.get(id=input.id)
        if post.source.user != user:
            raise Exception("Not authorized!")

        post.read = True
        post.save()
        return Read(ok=ok)


class refreshInput(graphene.InputObjectType):
    force = graphene.Boolean()

class RefreshFeeds(graphene.Mutation):
    class Arguments:
        input = refreshInput(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, input=None):
        update_feeds(30, user=info.context.user)
        return RefreshFeeds(ok=True)


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)
    token = graphene.String()
    refresh_token = graphene.String()

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String(required=True)

    def mutate(self, info, username, password, email):
        user = get_user_model()(
            username=username,
            email=email,
        )
        user.set_password(password)
        user.save()

        token = get_token(user)
        refresh_token = create_refresh_token(user)

        return CreateUser(user=user, token=token, refresh_token=refresh_token)


class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    verify_token = graphql_jwt.Verify.Field()
    add_source = AddSource.Field()
    refresh_feeds = RefreshFeeds.Field()
    remove_source = RemoveSource.Field()
    mark_as_read = Read.Field()


class Query(graphene.ObjectType):
    all_feeds = graphene.List(PostType, unread=graphene.Boolean())
    all_sources = graphene.List(SourceType)
    one_feed = graphene.List(PostType, source_id=graphene.Int(), unread=graphene.Boolean())

    def resolve_one_feed(self, info, source_id, unread):
        user = info.context.user
        if unread:
            posts = Post.objects.filter(source__user=user, source=source_id, read=False)
        else:
            posts = Post.objects.filter(source__user=user, source=source_id)
        return posts

    def resolve_all_sources(self, info):
        user = info.context.user
        sources = Source.objects.filter(user=user)
        return sources

    def resolve_all_feeds(self, info, unread):
        user = info.context.user
        if unread:
            posts = Post.objects.filter(source__user=user, read=False).order_by('-created')
        else:
            posts = Post.objects.filter(source__user=user).order_by('-created')
        return posts

schema = graphene.Schema(query=Query, mutation=Mutation)
