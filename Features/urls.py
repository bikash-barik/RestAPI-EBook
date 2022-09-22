from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf.urls.static import static
from django.conf import settings
from FeatureApp.views import MyObtainTokenPairView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('FeatureApp.urls')),
    path('api-auth/', include('rest_framework.urls')),
    # path('login/', TokenObtainPairView.as_view()),
    path('login/', MyObtainTokenPairView.as_view()),
    # path('login/', TokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view())
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

