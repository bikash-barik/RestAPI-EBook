from django.urls import path
from django.conf.urls.static import static
from . import views
from .views import *

urlpatterns = [
                  # User registration Api's
                  path('email-verify/', VerifyEmail.as_view(), name="email-verify"),
                  path('password-reset/<uidb64>/<token>/', PasswordTokenCheckAPI.as_view(),
                       name='password-reset-confirm'),
                  path('request-reset-email/', RequestPasswordResetEmail.as_view(), name='request-reset-email'),
                  path('password-reset-complete/', SetNewPasswordAPIView.as_view(), name='password-reset-complete'),
                  path('register/', RegisterView.as_view(), name='auth_register'),
                  path('resendemail/', ResendVerifyEmail.as_view()),

                  # Migration Api's
                  path('migrationcreate/', views.migrationcreate, name='migrationcreate'),

                  # Object types Api's
                  path('object_type_create/', views.object_type_create, name='object_type_create'),

                  # Feature Api's
                  path('featurecreate/', views.featurecreate, name='featurecreate'),

                  # Approval Api's
                  # path('approval_request_create/', views.approval_request_create, name='approval_request_create'),

                  # Menu Creation Api's
                  path('menu_view_creation/', views.menu_view_creation, name='menu_view_creation'),



              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

