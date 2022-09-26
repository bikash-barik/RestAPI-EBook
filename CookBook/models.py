from django.db import models
from django.contrib.auth.models import AbstractUser
from .backend.custom_azure import AzureMediaStorage as AMS
import os


class Users(AbstractUser):
    is_verified = models.BooleanField(default=False)
    admin_migrations = models.TextField(null=True)
    user_migrations = models.TextField(null=True)
    is_user_admin = models.BooleanField(default=False)
    user_registration_status = models.TextField(default='Awaiting for admin approval')

class Migrations(models.Model):
    Project_Version_Id = models.CharField(max_length=100, default=0)
    Migration_Name = models.CharField(max_length=100)
    Project_Version_Limit = models.CharField(max_length=50, blank=True)
    Feature_Version_Limit = models.CharField(max_length=50, blank=True)

class ObjectTypes(models.Model):
    Object_Id = models.BigAutoField(primary_key=True)
    Project_Version_Id = models.CharField(max_length=100, default=0)
    Migration_Name = models.CharField(max_length=100)
    Object_Type = models.CharField(max_length=100, blank=True)
    Parent_Object_Id = models.CharField(max_length=50, blank=True)

class Features(models.Model):
    Feature_Id = models.BigAutoField(primary_key=True)
    Migration_Name = models.CharField(max_length=100)
    Project_Version_Id = models.SmallIntegerField(default=0)
    Feature_Version_Id = models.SmallIntegerField(default=0)
    Object_Id = models.ForeignKey(ObjectTypes, on_delete=models.CASCADE, null=True)
    Feature_Name = models.CharField(max_length=100)
    Feature_version_approval_status = models.CharField(max_length=50, default='In Progress')
    Keywords = models.TextField(blank=True, null=True)
    Estimations = models.TextField(blank=True, null=True)
    Sequence = models.CharField(max_length=50)
    Source_FeatureDescription = models.TextField(blank=True, null=True)
    Target_FeatureDescription = models.TextField(blank=True, null=True)
    Source_Code = models.TextField(blank=True, null=True)
    Conversion_Code = models.TextField(blank=True, null=True)
    Target_Expected_Output = models.TextField(blank=True, null=True)
    Target_Actual_Output = models.TextField(blank=True, null=True)
    Feature_Created_by = models.CharField(max_length=100, null=True, blank=True)
    Feature_Created_at = models.DateField(auto_now_add=True)
    Last_Modified_by = models.CharField(max_length=100, null=True, blank=True)
    Last_Modified_at = models.DateField(null=True, blank=True)
    Feature_Requested_By = models.CharField(max_length=100, null=True, blank=True)
    Feature_Requested_Date = models.DateField(null=True, blank=True)
    Feature_Approval_Date = models.DateField(blank=True, null=True)

def user_directory_path(instance, Filename):
    path_file = 'media/' + instance.Feature_Id.Migration_TypeId + '/' + 'Project_V' + str(
        instance.Feature_Id.Project_Version_Id) + '/' + instance.Feature_Id.Object_Type + '/' + instance.Feature_Id.Feature_Name + '/' + 'Feature_V' + str(
        instance.Feature_Id.Feature_Version_Id) + '/' + instance.AttachmentType + '/' + Filename
    if os.path.exists(path_file):
        os.remove(path_file)
    for row in Attachments.objects.all().reverse():
        if Attachments.objects.filter(filename=row.filename, AttachmentType=row.AttachmentType,
                                      Feature_Id_id=row.Feature_Id_id).count() > 1:
            row.delete()
    return 'media/{0}/Project_V{1}/{2}/{3}/Feature_V{4}/{5}/{6}'.format(instance.Feature_Id.Migration_TypeId,
                                                                        instance.Feature_Id.Project_Version_Id,
                                                                        instance.Feature_Id.Object_Type,
                                                                        instance.Feature_Id.Feature_Name,
                                                                        instance.Feature_Id.Feature_Version_Id,
                                                                        instance.AttachmentType, Filename)

class Attachments(models.Model):
    Choices = [
        ('Source Description', 'source description'),
        ('Target Description', 'target description'),
        ('Source Code', 'source code'),
        ('Conversion Code', 'conversion code'),
        ('Actual Target Code', 'actual target code'),
        ('Expected Target Code', 'expected target code')
    ]
    Feature_Id = models.ForeignKey(Features, on_delete=models.CASCADE, null=True)
    Project_Version_Id = models.SmallIntegerField(default=0)
    Feature_Version_Id = models.SmallIntegerField(default=0)
    Attachment_Type = models.CharField(max_length=50, blank=True, null=True, choices=Choices)
    Filename = models.CharField(max_length=100, blank=True, null=True)
    Attachment = models.FileField(upload_to=user_directory_path, blank=True, null=True, storage=AMS,
                                  max_length=500)


class Approvals(models.Model):
    User_Email = models.CharField(max_length=100)
    Migration_Name = models.CharField(max_length=50, null=True)
    Approval_Request = models.CharField(max_length=1000)
    Access_Type = models.CharField(max_length=100)
    Approval_Status = models.CharField(max_length=100)
    Approved_by = models.CharField(max_length=100, null=True, blank=True)
    Created_at = models.DateField(auto_now_add=True)
    Expiry_date = models.DateField(null=True, blank=True)

class Permissions(models.Model):
    User_Email = models.CharField(max_length=100)
    Migration_Name = models.CharField(max_length=100, null=True)
    Parent_Object_Type = models.CharField(max_length=100)
    Access_Type = models.CharField(max_length=100)
    Current_Permissions = models.CharField(max_length=10000)











