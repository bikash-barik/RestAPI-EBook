from django.contrib import admin
from .models import Feature, Attachments, Users,Permissions, migrations, Approvals,Deploy

# Register your models here.

admin.site.register(Feature)
admin.site.register(Attachments)
admin.site.register(Users)
admin.site.register(Permissions)
admin.site.register(migrations)
admin.site.register(Approvals)
admin.site.register(Deploy)
