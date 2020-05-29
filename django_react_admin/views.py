from django.conf.urls import url
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path, reverse
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, views, pagination
from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework.decorators import action, MethodMapper
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.reverse import reverse_lazy
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer

router = DefaultRouter()
r = Request(HttpRequest())
r.user = get_user_model()(is_superuser=True)


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'  # items per page


def get_serializer_class(model, model_admin):
    meta_props = {
        "model": model,
        "fields": list(model_admin.get_fields(r)),
        "read_only_fields": model_admin.readonly_fields
    }
    return type(
        f"{model.__name__}Serializer",
        (ModelSerializer,),
        {"Meta": type("Meta", (), meta_props)},
    )


for model, model_admin in admin.site._registry.items():

    def get_info(model_admin):
        def info(*args):
            basic_params = {
                "fields": list(model_admin.get_fields(r)),
                "list_display": list(model_admin.get_list_display(r)),
                "ordering_fields": list(model_admin.get_sortable_by(r)),
                "filterset_fields": list(model_admin.get_list_filter(r)),
            }
            form = [
                dict(name=name, **field.widget.__dict__)
                for name, field in model_admin.get_form(r)().fields.items()
                if not hasattr(field.widget, "widget")
            ]
            return Response(
                    dict(form=form, **basic_params)
            )
        return info

    queryset = model.objects.all()
    if model_admin.list_select_related:
        queryset = queryset.select_related(*model_admin.list_select_related)

    params = {
        "queryset": queryset,
        "filter_backends": [DjangoFilterBackend, OrderingFilter],
        "info": action(methods=["get"], detail=False)(get_info(model_admin)),
        "serializer_class": get_serializer_class(model, model_admin),
        "basename": model._meta.model_name,
        "request": r,
        "fields": list(model_admin.get_fields(r)),
        "list_display": list(model_admin.get_list_display(r)),
        "ordering_fields": list(model_admin.get_sortable_by(r)),
        "filterset_fields": list(model_admin.get_list_filter(r)),
        "permission_classes": [permissions.IsAdminUser, permissions.DjangoModelPermissions],
        "pagination_class": CustomPageNumberPagination
    }
    viewset = type(f"{model.__name__}ViewSet", (viewsets.ModelViewSet,), params)
    router.register(
        f"{model._meta.app_label}/{model._meta.model_name}", viewset
    )
    viewpath = f"{model._meta.app_label}/{model._meta.model_name}"
    # urlpatterns.append(
    #     path(
    #         r"html/{}/".format(viewpath),
    #         TemplateView.as_view(
    #             template_name="django_react_admin/list.html",
    #             extra_context={
    #                 "app": model._meta.app_label,
    #                 "model": model._meta.model_name,
    #                 "path": reverse_lazy(model._meta.model_name+"-list"),
    #             },
    #         ),
    #     )
    # )
    # urlpatterns.append(
    #     path(
    #         r"html/{}/add/".format(viewpath),
    #         TemplateView.as_view(
    #             template_name="django_react_admin/edit.html",
    #             extra_context={
    #                 "create": True,
    #                 "app": model._meta.app_label,
    #                 "model": model._meta.model_name,
    #                 "path": reverse_lazy(model._meta.model_name + "-list"),
    #             },
    #         ),
    #     )
    # )
    # urlpatterns.append(
    #     path(
    #         r"html/{}/<pk>/".format(viewpath),
    #         TemplateView.as_view(
    #             template_name="django_react_admin/edit.html",
    #             extra_context={
    #                 "create": False,
    #                 "app": model._meta.app_label,
    #                 "model": model._meta.model_name,
    #                 "path": reverse_lazy(model._meta.model_name + "-list"),
    #             },
    #         ),
    #     )
    # )


class Index(views.APIView):
    def get(self, request):
        res = admin.site.get_app_list(request)
        # return Response([m['admin_url'].replace(reverse('admin:index'), '') for app in res for m in app['models']])
        for app in res:
            app['app_url'] = app['app_url'].replace(reverse('admin:index'), '')
            for m in app['models']:
                for k in ['add_url', 'admin_url']:
                    m[k] = m[k].replace(reverse('admin:index'), '')
        return Response(res)


urlpatterns = [path('', Index.as_view(), name='react_admin_index')] + router.urls
