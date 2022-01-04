from django.conf.urls import url
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path, reverse
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, views, pagination
from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework.decorators import action, MethodMapper
from rest_framework.filters import OrderingFilter, SearchFilter
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


# def get_serializer_class(model, model_admin):
#     meta_props = {
#         "model": model,
#         "fields": list(model_admin.get_fields(r)),
#         "read_only_fields": model_admin.readonly_fields
#     }
#     return type(
#         f"{model.__name__}Serializer",
#         (ModelSerializer,),
#         {"Meta": type("Meta", (), meta_props)},
#     )

def get_serializer_class(self):
    meta_props = {
        "model": self.model,
        "fields": list(self.model_admin.get_fields(self.request)),
        "read_only_fields": self.model_admin.readonly_fields
    }

    return type(
        f"{model.__name__}Serializer",
        (ModelSerializer,),
        {"Meta": type("Meta", (), meta_props)}
    )

def model_views_set_list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())

    page = self.paginate_queryset(queryset)
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    serializer = self.get_serializer(queryset, many=True)
    headers = {
        "X-Total-Count": queryset.count()
    }

    return Response(
        serializer.data,
        headers=headers
    )

for model, model_admin in admin.site._registry.items():

    def get_filterset_fields(model_admin):
        filterset_fields = {}
        for filterset_field in list(model_admin.get_list_filter(r)):
            if isinstance(filterset_field, str):
                filterset_field_name = filterset_field
            else:
                filterset_field_name = filterset_field[0]

            filterset_fields[filterset_field_name] = ['gte', 'lte', 'exact', 'gt', 'lt']

        return filterset_fields

    # def get_info(model_admin):
    #     def info(*args):
    #         basic_params = {
    #             "fields": list(model_admin.get_fields(r)),
    #             "list_display": list(model_admin.get_list_display(r)),
    #             "ordering_fields": list(model_admin.get_sortable_by(r)),
    #             "filterset_fields": get_filterset_fields(model_admin),
    #         }
    #         form = [
    #             dict(name=name, **field.widget.__dict__)
    #             for name, field in model_admin.get_form(r)().fields.items()
    #             if not hasattr(field.widget, "widget")
    #         ]
    #         return Response(
    #             dict(form=form, **basic_params),
    #         )
    #     return info

    def get_info(self):
        def info(*args):
            basic_params = {
                "fields": list(self.model_admin.get_fields(self.request)),
                "list_display": list(model_admin.get_list_display(self.request)),
                "ordering_fields": list(self.model_admin.get_sortable_by(self.request)),
                "filterset_fields": get_filterset_fields(self.model_admin)
            }

            form = [
                dict(name=name, **field.widget.__dict__)
                for name, field in self.model_admin.get_form(self.request)().fields.items()
                if not hasattr(field.widget, "widget")
            ]
            return Response(
                dict(form=form, **basic_params)
            )

        return info

    def get_queryset(self):
        queryset = self.model_admin.get_queryset(self.request)

        return queryset

    if not hasattr(model, 'objects'):
        continue  # Use case: dramatiq.models.Task

    # queryset = model_admin.get_queryset(r)
    if model_admin.list_select_related:
        queryset = queryset.select_related(*model_admin.list_select_related)

    params = {
        # "queryset": queryset,
        "model": model,
        "model_admin": model_admin,
        "get_queryset": get_queryset,
        "filter_backends": [DjangoFilterBackend, OrderingFilter, SearchFilter],
        # "info": action(methods=["get"], detail=False)(get_info(model_admin)),
        "info": get_info,
        # "serializer_class": get_serializer_class(model, model_admin),
        "get_serializer_class": get_serializer_class,
        "basename": model._meta.model_name,
        "request": r,
        # "fields": list(model_admin.get_fields(r)),
        "filterset_class":  getattr(model_admin, 'filterset_class', None),
        "list_display": list(model_admin.get_list_display(r)),
        "ordering_fields": list(model_admin.get_sortable_by(r)),
        "filterset_fields": get_filterset_fields(model_admin),
        "search_fields": list(model_admin.get_search_fields(r)),
        "permission_classes": getattr(
            model_admin, 'permission_classes',
            [permissions.DjangoModelPermissions]
        ),
        "pagination_class": CustomPageNumberPagination,
        "list": model_views_set_list
    }
    viewset = type(f"{model.__name__}ViewSet", (viewsets.ModelViewSet,), params)
    router.register(
        f"{model._meta.app_label}/{model._meta.model_name}", viewset, model._meta.model_name
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
                    if k not in m or not m[k]:
                        continue  # Use case: dramatiq.models.Task

                    m[k] = m[k].replace(reverse('admin:index'), '')
        return Response(res)


urlpatterns = [path('', Index.as_view(), name='react_admin_index')] + router.urls
