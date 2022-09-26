from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from CookBook.views import MyObtainTokenPairView
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('CookBook.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('login/', MyObtainTokenPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view())
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
