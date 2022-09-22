import mimetypes,json,re,sys,jwt,xlsxwriter,shutil
from azure.storage.blob import BlobServiceClient,ResourceTypes,AccountSasPermissions,generate_account_sas
from rest_framework import status,generics
from .serializers import *
from datetime import *
from config.config import frontend_url, fileshare_connectionString, container_name_var,account_name,account_key
from .backend.custom_azure import azure_connection
from .models import *
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import HttpResponse
from import_file import import_file
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from Features.settings import EMAIL_HOST_USER
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q


@api_view(['GET'])
def featurelist(request):
    features = Feature.objects.all()
    serializer = FeatureSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def featurecreate(request):
    migration_type = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    project_version = request.data['Project_Version_Id']

    feature_data = Feature.objects.filter(Project_Version_Id=project_version, Migration_TypeId=migration_type,
                                          Object_Type=object_type,
                                          Feature_Name=feature_name)
    if feature_data:
        return Response("Feature already present with this version.Kindly request access for it")
    else:
        serializer = FeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(Feature_Version_Id=int(request.data['Feature_Version_Id']) + 1)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def featuredropdownlist(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    migtype = body_data['Migration_TypeId']
    obj_type = body_data['Object_Type']
    features = Feature.objects.filter(
        Object_Type=obj_type, Migration_TypeId=migtype)
    serializer = FeaturedropdownSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def feature_version_list(request):
    mig_type = request.data['Migration_Type']
    obj_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    project_version = request.data['Project_Version_Id']

    version_list = []
    inter_dict = {}
    final_list = []
    features = Feature.objects.filter(Project_Version_Id=project_version, Migration_TypeId=mig_type,
                                      Object_Type=obj_type, Feature_Name=feature_name)
    for dict in features.values():
        version_list.append(dict['Feature_Version_Id'])
    version_list = sorted(version_list)
    for ver in version_list:
        inter_dict['title'] = str(ver)
        inter_dict['code'] = ver
        final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['POST'])
def featuredetail(request, feature_name):
    email = request.data['User_Email']
    mig_type = request.data['Migration_Type']
    obj_type = request.data['Object_Type']
    Project_Version_Id = request.data['Project_Version_Id']
    mig_data = migrations.objects.filter(Migration_TypeId=mig_type, Object_Type=obj_type)
    project_versions_list = []
    for dict in mig_data.values():
        project_versions_list.append(dict['Project_Version_Id'])
    max_project_version = max(project_versions_list)
    # user = Users.objects.filter(email=email)
    #
    # user_values = list(user.values())
    # admin_access = user_values[0]['admin_migrations']
    # if admin_access == '' or admin_access == None:
    #     admin_access_dict = {}
    # else:
    #     admin_access = admin_access.replace("\'", "\"")
    #     admin_access_dict = json.loads(admin_access)

    user = Users.objects.get(email=email)

    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)

    final_list = []
    version_list = []
    features = Feature.objects.filter(Migration_TypeId=mig_type, Object_Type=obj_type, Feature_Name=feature_name,
                                      Project_Version_Id=Project_Version_Id)
    for dict in features.values():
        version_list.append(dict['Feature_Version_Id'])
    max_version = max(version_list)

    for obj in features:
        mig_type = obj.Migration_TypeId
        obj_type = obj.Object_Type
        feature_name = obj.Feature_Name
        feature_id = obj.Feature_Id
        feature_version_id = obj.Feature_Version_Id
        f_approval = obj.Feature_version_approval_status
        f_project_version = obj.Project_Version_Id
        EDIT = 0
        latest_flag = 0
        max_project_flag = 0
        if int(f_project_version) < int(max_project_version):
            if mig_type in admin_access_dict.keys():
                if obj_type in admin_access_dict[mig_type] or 'ALL' in admin_access_dict[mig_type]:
                    EDIT = 1
                else:

                    perm_data3 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type='ALL')
                    if perm_data3:
                        data3_access = perm_data3.values()[0]['Access_Type']
                        if data3_access in ('Edit', 'ALL'):
                            EDIT = 1

                    perm_data2 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type, Feature_Name='ALL')
                    if perm_data2:
                        data2_access = perm_data2.values()[0]['Access_Type']
                        if data2_access in ('Edit', 'ALL'):
                            EDIT = 1
                    perm_data1 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type, Feature_Name=feature_name)
                    if perm_data1:
                        data1_access = perm_data1.values()[0]['Access_Type']
                        if data1_access in ('Edit', 'ALL'):
                            EDIT = 1

                    if not perm_data1 and perm_data2 and perm_data3:
                        EDIT = 0
                if feature_version_id < max_version and f_approval == 'Approved':
                    latest_flag = 0
                elif feature_version_id == max_version and f_approval == 'Approved':
                    latest_flag = 0
                else:
                    latest_flag = 1
            else:
                perm_data3 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type, Object_Type='ALL')
                if perm_data3:
                    data3_access = perm_data3.values()[0]['Access_Type']
                    if data3_access in ('Edit', 'ALL'):
                        EDIT = 1
                perm_data2 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name='ALL')
                if perm_data2:
                    data2_access = perm_data2.values()[0]['Access_Type']
                    if data2_access in ('Edit', 'ALL'):
                        EDIT = 1
                perm_data1 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name=feature_name)
                if perm_data1:
                    data1_access = perm_data1.values()[0]['Access_Type']
                    if data1_access in ('Edit', 'ALL'):
                        EDIT = 1
                if not perm_data1 and perm_data2 and perm_data3:
                    EDIT = 0
                if feature_version_id < max_version and f_approval == 'Approved':
                    latest_flag = 0
                elif feature_version_id == max_version and f_approval == 'Approved':
                    latest_flag = 0
                else:
                    latest_flag = 1
            max_project_flag = 0
        elif int(f_project_version) == int(max_project_version):
            if mig_type in admin_access_dict.keys():
                if obj_type in admin_access_dict[mig_type] or 'ALL' in admin_access_dict[mig_type]:
                    EDIT = 1
                else:

                    perm_data3 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type='ALL')
                    if perm_data3:
                        data3_access = perm_data3.values()[0]['Access_Type']
                        if data3_access in ('Edit', 'ALL'):
                            EDIT = 1

                    perm_data2 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type, Feature_Name='ALL')
                    if perm_data2:
                        data2_access = perm_data2.values()[0]['Access_Type']
                        if data2_access in ('Edit', 'ALL'):
                            EDIT = 1
                    perm_data1 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type, Feature_Name=feature_name)
                    if perm_data1:
                        data1_access = perm_data1.values()[0]['Access_Type']
                        if data1_access in ('Edit', 'ALL'):
                            EDIT = 1

                    if not perm_data1 and perm_data2 and perm_data3:
                        EDIT = 0
                if feature_version_id < max_version and f_approval == 'Approved':
                    latest_flag = 0
                elif feature_version_id == max_version and f_approval == 'Approved':
                    latest_flag = 0
                else:
                    latest_flag = 1
            else:
                perm_data3 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type, Object_Type='ALL')
                if perm_data3:
                    data3_access = perm_data3.values()[0]['Access_Type']
                    if data3_access in ('Edit', 'ALL'):
                        EDIT = 1
                perm_data2 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name='ALL')
                if perm_data2:
                    data2_access = perm_data2.values()[0]['Access_Type']
                    if data2_access in ('Edit', 'ALL'):
                        EDIT = 1
                perm_data1 = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name=feature_name)
                if perm_data1:
                    data1_access = perm_data1.values()[0]['Access_Type']
                    if data1_access in ('Edit', 'ALL'):
                        EDIT = 1
                if not perm_data1 and perm_data2 and perm_data3:
                    EDIT = 0

                if feature_version_id < max_version and f_approval == 'Approved':
                    latest_flag = 0
                elif feature_version_id == max_version and f_approval == 'Approved':
                    latest_flag = 0
                else:
                    latest_flag = 1
            max_project_flag = 1
        if feature_version_id < max_version and f_approval == 'Approved':
            max_flag = 0
        elif feature_version_id == max_version and f_approval == 'Approved':
            max_flag = 1
        elif feature_version_id == max_version:
            if f_approval == 'In Progress' or f_approval == 'Awaiting Approval':
                max_flag = 1
        else:
            max_flag = 0

        feature = Feature.objects.get(Feature_Id=feature_id)
        serializer = FeatureSerializer(feature, many=False)
        response = {'edit': EDIT, 'Latest_Flag': latest_flag, 'Max_Flag': max_flag,
                    'Max_Project_Flag': max_project_flag, 'serializer': serializer.data}
        final_list.append(response)
    return Response(final_list)


@api_view(['GET', 'POST'])
def feature_catalog_access_check(request):
    user_email = request.data['User_Email']
    mig_type = request.data['Migration_Type']
    obj_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    Project_Version_Id = request.data['Project_Version_Id']

    # user = Users.objects.filter(email=user_email)
    #
    # user_values = list(user.values())
    # admin_access = user_values[0]['admin_migrations']
    # if admin_access == '' or admin_access == None:
    #     admin_access_dict = {}
    # else:
    #     admin_access = admin_access.replace("\'", "\"")
    #     admin_access_dict = json.loads(admin_access)

    user = Users.objects.get(email=user_email)

    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)

    flag = 1
    view_flag = 0
    if obj_type == 'ALL' or feature_name == 'ALL':
        if mig_type in admin_access_dict.keys():
            if obj_type in admin_access_dict[mig_type] or 'ALL' in admin_access_dict[mig_type]:
                flag = 3
            else:

                perm_data3 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                        Object_Type='ALL')
                if perm_data3:
                    data3_access = perm_data3.values()[0]['Access_Type']
                    if data3_access in ('Edit', 'ALL'):
                        flag = 3
                    elif data3_access == 'View':
                        flag = 2
                    else:
                        flag = 1
                perm_data2 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name='ALL')
                if perm_data2:
                    data2_access = perm_data2.values()[0]['Access_Type']
                    if data2_access in ('Edit', 'ALL'):
                        flag = 3
                    elif data2_access == 'View':
                        flag = 2
                    else:
                        flag = 1
                perm_data1 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type,
                                                        Feature_Name=feature_name)
                if perm_data1:
                    data1_access = perm_data1.values()[0]['Access_Type']
                    if data1_access in ('Edit', 'ALL'):
                        flag = 3
                    elif data1_access == 'View':
                        flag = 2
                    else:
                        flag = 1

                if not perm_data1 and perm_data2 and perm_data3:
                    flag = 1
        elif obj_type != '' and feature_name != '':
            perm_data3 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type, Object_Type='ALL')
            if perm_data3:
                data3_access = perm_data3.values()[0]['Access_Type']
                if data3_access in ('Edit', 'ALL'):
                    flag = 3
                elif data3_access == 'View':
                    flag = 2
                else:
                    flag = 1

            perm_data2 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                    Object_Type=obj_type,
                                                    Feature_Name='ALL')
            if perm_data2:
                data2_access = perm_data2.values()[0]['Access_Type']
                if data2_access in ('Edit', 'ALL'):
                    flag = 3
                elif data2_access == 'View':
                    flag = 2
                else:
                    flag = 1

            perm_data1 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                    Object_Type=obj_type,
                                                    Feature_Name=feature_name)
            if perm_data1:
                data1_access = perm_data1.values()[0]['Access_Type']
                if data1_access in ('Edit', 'ALL'):
                    flag = 3
                elif data1_access == 'View':
                    flag = 2
                else:
                    flag = 1

            if not perm_data1 and perm_data2 and perm_data3:
                flag = 1
        response = {'serializer': 'No Data', 'flag': flag, 'view_flag': 'No Data'}
    else:
        features = Feature.objects.filter(Migration_TypeId=mig_type, Project_Version_Id=Project_Version_Id,
                                          Object_Type=obj_type, Feature_Name=feature_name)
        version_list = []
        for dict in features.values():
            version_list.append(dict['Feature_Version_Id'])
        max_version = max(version_list)
        for obj in features:
            mig_type = obj.Migration_TypeId
            obj_type = obj.Object_Type
            feature_name = obj.Feature_Name
            feature_id = obj.Feature_Id
            feature_version_id = obj.Feature_Version_Id
            f_approval = obj.Feature_version_approval_status
            if feature_version_id == max_version:
                if mig_type in admin_access_dict.keys():
                    if obj_type in admin_access_dict[mig_type] or 'ALL' in admin_access_dict[mig_type]:
                        flag = 3
                    else:

                        perm_data3 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                                Object_Type='ALL')
                        if perm_data3:
                            data3_access = perm_data3.values()[0]['Access_Type']
                            if data3_access in ('Edit', 'ALL'):
                                flag = 3
                            elif data3_access == 'View':
                                flag = 2
                            else:
                                flag = 1
                        perm_data2 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                                Object_Type=obj_type,
                                                                Feature_Name='ALL')
                        if perm_data2:
                            data2_access = perm_data2.values()[0]['Access_Type']
                            if data2_access in ('Edit', 'ALL'):
                                flag = 3
                            elif data2_access == 'View':
                                flag = 2
                            else:
                                flag = 1
                        perm_data1 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                                Object_Type=obj_type,
                                                                Feature_Name=feature_name)
                        if perm_data1:
                            data1_access = perm_data1.values()[0]['Access_Type']
                            if data1_access in ('Edit', 'ALL'):
                                flag = 3
                            elif data1_access == 'View':
                                flag = 2
                            else:
                                flag = 1

                        if not perm_data1 and perm_data2 and perm_data3:
                            flag = 1
                elif obj_type != '' and feature_name != '':
                    perm_data3 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                            Object_Type='ALL')
                    if perm_data3:
                        data3_access = perm_data3.values()[0]['Access_Type']
                        if data3_access in ('Edit', 'ALL'):
                            flag = 3
                        elif data3_access == 'View':
                            flag = 2
                        else:
                            flag = 1

                    perm_data2 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type,
                                                            Feature_Name='ALL')
                    if perm_data2:
                        data2_access = perm_data2.values()[0]['Access_Type']
                        if data2_access in ('Edit', 'ALL'):
                            flag = 3
                        elif data2_access == 'View':
                            flag = 2
                        else:
                            flag = 1

                    perm_data1 = Permissions.objects.filter(User_Email=user_email, Migration_TypeId=mig_type,
                                                            Object_Type=obj_type,
                                                            Feature_Name=feature_name)
                    if perm_data1:
                        data1_access = perm_data1.values()[0]['Access_Type']
                        if data1_access in ('Edit', 'ALL'):
                            flag = 3
                        elif data1_access == 'View':
                            flag = 2
                        else:
                            flag = 1

                    if not perm_data1 and perm_data2 and perm_data3:
                        flag = 1
                if feature_version_id == max_version and f_approval == 'Pending':
                    view_flag = 0
                elif feature_version_id == max_version and f_approval == 'Approved':
                    view_flag = 1
                else:
                    view_flag = 0
            if feature_name != 'ALL' and obj_type != 'ALL':
                features = Feature.objects.get(Feature_Id=feature_id)
                serializer = FeatureSerializer(features, many=False)
                response = {'serializer': serializer.data, 'flag': flag, 'view_flag': view_flag}
            else:
                response = {'serializer': 'No Data', 'flag': flag, 'view_flag': view_flag}
    return Response(response)


@api_view(['PUT'])
def featureupdate(request, pk):
    feature_approval_status_request = request.data['Feature_version_approval_status']
    feature = Feature.objects.get(Feature_Id=pk)
    project_id = feature.Project_Version_Id
    mig_type = feature.Migration_TypeId
    obj_type = feature.Object_Type
    feature_name = feature.Feature_Name
    feature_version = feature.Feature_Version_Id

    if feature_approval_status_request == 'Awaiting Approval':
        feature_data = Feature.objects.filter(Project_Version_Id=project_id, Migration_TypeId=mig_type,
                                              Object_Type=obj_type, Feature_Name=feature_name,
                                              Feature_Version_Id=feature_version,
                                              Feature_version_approval_status='Awaiting Approval')
        if feature_data:
            return Response("Request for approval already present.Please wait for admin to approve it")
        else:
            serializer = FeatureSerializer(instance=feature, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        serializer = FeatureSerializer(instance=feature, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def att_list(request):
    att = Attachments.objects.all()
    serializer = AttachementSerializer(att, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def Sourcedescription(request, id):
    features = Attachments.objects.filter(
        Feature_Id=id, AttachmentType='Sourcedescription')
    serializer = AttachementSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def Targetdescription(request, id):
    features = Attachments.objects.filter(
        Feature_Id=id, AttachmentType='Targetdescription')
    serializer = AttachementSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def Conversion(request, id):
    features = Attachments.objects.filter(
        Feature_Id=id, AttachmentType='Conversion')
    serializer = AttachementSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def attachment_delete(request):
    id = request.data['id']
    attachment = Attachments.objects.get(id=id)
    blob_path = attachment.Attachment
    container_client = azure_connection()
    blob_check = container_client.list_blobs(name_starts_with=blob_path)
    if blob_check:
        for blob in blob_check:
            container_client.delete_blobs(blob)
    attachment.delete()
    return Response('Deleted')

@api_view(['POST'])
def Attcahmentupdate(request, pk):
    feature = Feature.objects.get(Feature_Id=pk)
    AttachmentType = request.data['AttachmentType']
    Attachment = request.FILES['Attachment']
    filename = request.data['filename']
    project_id = feature.Project_Version_Id
    feature_version_id = feature.Feature_Version_Id
    dictionary = {"Feature_Id": feature, 'Project_Version_Id': project_id, 'Feature_Version_Id': feature_version_id,
                  'AttachmentType': AttachmentType, "filename": filename,
                  "Attachment": Attachment}
    attachements = AttachementSerializer(data=dictionary)
    if attachements.is_valid():
        attachements.save()
        for row in Attachments.objects.all().reverse():
            if Attachments.objects.filter(filename=row.filename, AttachmentType=row.AttachmentType,
                                          Feature_Id_id=row.Feature_Id_id).count() > 1:
                row.delete()
        return Response(attachements.data, status=status.HTTP_200_OK)
    return Response(attachements.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE','POST'])
def featuredelete(request, feature_name):
    Project_Version_Id = request.data['Project_Version_Id']
    migration_typeid = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']
    features = Feature.objects.filter(Project_Version_Id=Project_Version_Id, Feature_Name=feature_name)
    feature_id_list = []
    for dict in features.values():
        feature_id_list.append(dict['Feature_Id'])
    for id in feature_id_list:
        att_data = Attachments.objects.filter(Project_Version_Id=Project_Version_Id, Feature_Id_id=id)
        if att_data:
            att_data.delete()
    appr_data = Approvals.objects.filter(Feature_Name=feature_name)
    perm_data = Permissions.objects.filter(Feature_Name=feature_name)
    appr_data.delete()
    perm_data.delete()
    features.delete()
    fileshare_path = 'media/' + migration_typeid + '/' + 'Project_V' + str(
        Project_Version_Id) + '/' + object_type + '/' + feature_name + '/'
    container_client = azure_connection()
    del_blobs = container_client.list_blobs(name_starts_with=fileshare_path)
    if del_blobs:
        for blob in del_blobs:
            container_client.delete_blobs(blob)
    return Response('Deleted')


@api_view(['POST'])
def predessors(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    Object_Type = body_data['Object_Type']
    Migration_TypeId = body_data['Migration_TypeId']
    Project_Version_Id = body_data['Project_Version_Id']
    features = Feature.objects.filter(
        Object_Type=Object_Type, Migration_TypeId=Migration_TypeId, Project_Version_Id=Project_Version_Id)
    serializer = SequenceSerializer(features, many=True)
    feature_list = []
    final_list = []
    final_dict = {}
    for dict in serializer.data:
        feature_list.append(dict['Feature_Name'])
    feature_list = list(set(feature_list))
    for feature in feature_list:
        final_dict['Feature_Name'] = feature
        final_list.append(final_dict.copy())
    return Response(final_list, status=status.HTTP_200_OK)


@api_view(['POST'])
def download_attachment(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    file_name = body_data['file_name']
    attach_type = body_data['AttachmentType']
    fid = body_data['feature_id']
    filter_files = Attachments.objects.filter(
        Feature_Id=fid, AttachmentType=attach_type, filename=file_name)
    filter_values = list(filter_files.values_list())
    file_path = filter_values[0]
    container_client = azure_connection()
    data = container_client.get_blob_client(file_path[6]).download_blob().readall()
    data = data.decode()
    return HttpResponse(data)


@api_view(['POST'])
def conversion(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    feature_name = body_data['featurename']
    python_code = body_data['convcode']
    source_code = body_data['sourcecode']
    migration_typeid = body_data['migration_typeid']
    object_type = body_data['object_type']
    project_id = body_data['Project_Version_Id']
    feature_version_id = body_data['Feature_Version_Id']
    schema = ''
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    conversion_path = 'media/' + migration_typeid + '/' + 'Project_V' + str(
        project_id) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(
        feature_version_id) + '/' + 'Conversion/'
    container_client = azure_connection()
    conversion_file_blob = container_client.list_blobs(name_starts_with=conversion_path)
    if python_code != 'r@rawstringstart\'\'@rawstringend':
        module_path = 'Modules/' + migration_typeid + '/' + 'Project_V' + str(
            project_id) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(feature_version_id)
        local_module_path = path + '/Modules/' + migration_typeid + '/' + 'Project_V' + str(
            project_id) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(feature_version_id)
        sys.path.append(local_module_path)
        if not os.path.exists(local_module_path):
            os.makedirs(local_module_path)
        python_code = python_code.replace("r@rawstringstart'", '').replace("'@rawstringend", '')
        python_code = re.sub(r'\bdef\s(.*?)\(', 'def ' + feature_name.strip() + '(', python_code)
        file_path = module_path + '/' + str(feature_name).strip() + '.py'
        local_path = local_module_path + '/' + str(feature_name).strip() + '.py'
        with open(local_path, 'w') as f:
            f.write(python_code)
        blob_client = container_client.get_blob_client(blob=file_path)
        blob_client.upload_blob(python_code, overwrite=True)
        module = import_file(local_path)
        data = getattr(module, str(feature_name).strip())
        executableoutput = data(source_code, schema)
        shutil.rmtree(path + '/Modules')
        return Response(executableoutput, status=status.HTTP_200_OK)
    elif conversion_file_blob:
        file_data = ''
        for blob in conversion_file_blob:
            file_data = container_client.get_blob_client(blob).download_blob().readall()
            file_data = file_data.decode()
        local_module_path = path + '/Modules/' + migration_typeid + '/' + 'Project_V' + str(
            project_id) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(feature_version_id)
        sys.path.append(local_module_path)
        if not os.path.exists(local_module_path):
            os.makedirs(local_module_path)
        local_path = local_module_path + '/' + str(feature_name).strip() + '.py'
        with open(local_path, 'w') as f:
            f.write(file_data)
        module = import_file(local_path)
        data = getattr(module, str(feature_name).strip())
        executableoutput = data(source_code, schema)
        shutil.rmtree(path + '/Modules')
        return Response(executableoutput, status=status.HTTP_200_OK)
    else:
        return Response('No Conversion Module, please add Conversion Module before Convert')


@api_view(['GET'])
def miglevelobjects(request, migtypeid):
    objecttypes = ['Procedure', 'Function', 'Package', 'Index', 'Materialized view', 'Sequence', 'Synonym', 'Tabel',
                   'Trigger', 'Type', 'View']
    data_format_main = {}

    for index, i in enumerate(objecttypes):
        data_format = {}
        features = Feature.objects.filter(
            Object_Type=i, Migration_TypeId=migtypeid)
        serializer = migrationlevelfeatures(features, many=True)
        data = serializer.data
        if i == 'Index':
            lablename = i + 'es'
        else:
            lablename = i + 's'
        data_format['Label'] = lablename
        data_format['subMenu'] = data
        data_format_main[index + 1] = data_format
    datavalues = data_format_main.values()
    return Response(datavalues, status=status.HTTP_200_OK)


# @api_view(['GET'])
# def attachentsqlcodefiles(request, id):
#     data = Attachments.objects.all()
#     serializer = AttachementSerializer(data, many=True)
#     filenames = []
#     result = []
#     for x in serializer.data:
#         filenames.append(x['filename'])
#     filenames = list(set(filenames))
#     for x in filenames:
#         temp = {}
#         temp['filename'] = x
#         data1 = Attachments.objects.filter(
#             Feature_Id=id, filename=x, AttachmentType='Sourcecode')
#
#         a = list(data1.values_list())
#         if len(a) == 0:
#             temp['Sourcecode'] = 'N'
#         else:
#             temp['Sourcecode'] = 'Y'
#             temp['sid'] = a[0][0]
#         data1 = Attachments.objects.filter(
#             Feature_Id=id, filename=x, AttachmentType='Actualtargetcode')
#         a = list(data1.values_list())
#         if len(a) == 0:
#             temp['Actualtargetcode'] = 'N'
#         else:
#             temp['Actualtargetcode'] = 'Y'
#             temp['atid'] = a[0][0]
#         data1 = Attachments.objects.filter(
#             Feature_Id=id, filename=x, AttachmentType='Expectedconversion')
#         a = list(data1.values_list())
#         if len(a) == 0:
#             temp['Expectedconversion'] = 'N'
#         else:
#             temp['Expectedconversion'] = 'Y'
#             temp['etid'] = a[0][0]
#
#         if temp['Sourcecode'] == 'Y' or temp['Expectedconversion'] == 'Y' or temp['Actualtargetcode'] == 'Y':
#             result.append(temp)
#     return Response(result)

@api_view(['GET'])
def attachentsqlcodefiles(request, id):
    data = Attachments.objects.filter(Q(Feature_Id_id = id) & ~Q(AttachmentType ='Conversion'))
    serializer = AttachementSerializer(data, many=True)
    filenames = []
    result = []
    for dict in serializer.data:
        filenames.append(dict['filename'])
    filenames = list(set(filenames))
    for filename in filenames:
        temp = {}
        temp['filename'] = filename
        data1 = Attachments.objects.filter(
            Feature_Id=id, filename=filename, AttachmentType='Sourcecode')
        data_list = data1.values()
        if data1:
            temp['Sourcecode'] = 'Y'
            temp['sid'] = data_list[0]['id']
        else:
            temp['Sourcecode'] = 'N'
        data1 = Attachments.objects.filter(
            Feature_Id_id=id, filename=filename, AttachmentType='Actualtargetcode')
        data_list = data1.values()
        if data1:
            temp['Actualtargetcode'] = 'Y'
            temp['atid'] = data_list[0]['id']
        else:
            temp['Actualtargetcode'] = 'N'
        data1 = Attachments.objects.filter(
            Feature_Id=id, filename=filename, AttachmentType='Expectedconversion')
        data_list = data1.values()
        if data1:
            temp['Expectedconversion'] = 'Y'
            temp['etid'] = data_list[0]['id']
        else:
            temp['Expectedconversion'] = 'N'
        if temp['Sourcecode'] == 'Y' or temp['Expectedconversion'] == 'Y' or temp['Actualtargetcode'] == 'Y':
            result.append(temp)
    return Response(result)

@api_view(['POST'])
def feature_conversion_files(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    feature_id = body_data['Feature_Id']
    attach_type = body_data['AttachmentType']
    feature = body_data['Feature_Name']
    migid = body_data['Migration_TypeId']
    objtype = body_data['Object_Type']
    conversion_code = body_data['convcode']
    project_id = body_data['Project_Version_Id']
    feature_version_Id = body_data['Feature_Version_Id']
    schema = ''
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    module_path = 'media/' + migid + '/' + 'Project_V' + str(
        project_id) + '/' + objtype + '/' + feature + '/' + 'Feature_V' + str(
        feature_version_Id) + '/' + 'Conversion' + '/'
    container_client = azure_connection()
    conversion_file_blob = container_client.list_blobs(name_starts_with=module_path)
    if conversion_file_blob:
        file_data = ''
        for blob in conversion_file_blob:
            file_data = container_client.get_blob_client(blob).download_blob().readall()
            file_data = file_data.decode()
        local_module_path = path + '/Modules/' + migid + '/' + 'Project_V' + str(
            project_id) + '/' + objtype + '/' + feature + '/' + 'Feature_V' + str(feature_version_Id)
        if not os.path.exists(local_module_path):
            os.makedirs(local_module_path)
        local_path = local_module_path + '/' + str(feature).strip() + '.py'
        with open(local_path, 'w') as f:
            f.write(file_data)
    else:
        if conversion_code != 'r@rawstringstart\'\'@rawstringend':
            module_path = 'Modules/' + migid + '/' + 'Project_V' + str(
                project_id) + '/' + objtype + '/' + feature + '/' + 'Feature_V' + str(feature_version_Id)
            local_module_path = path + '/Modules/' + migid + '/' + 'Project_V' + str(
                project_id) + '/' + objtype + '/' + feature + '/' + 'Feature_V' + str(feature_version_Id)
            sys.path.append(local_module_path)
            if not os.path.exists(local_module_path):
                os.makedirs(local_module_path)
            conversion_code = conversion_code.replace("r@rawstringstart'", '').replace("'@rawstringend", '')
            conversion_code = re.sub(r'\bdef\s(.*?)\(', 'def ' + feature.strip() + '(', conversion_code)
            file_path = module_path + '/' + str(feature).strip() + '.py'
            local_path = local_module_path + '/' + str(feature).strip() + '.py'
            if os.path.isfile(local_path):
                os.remove(local_path)
            with open(local_path, 'w') as f:
                f.write(conversion_code)
            blob_client = container_client.get_blob_client(blob=file_path)
            blob_client.upload_blob(conversion_code, overwrite=True)
        else:
            return Response({"error": "Please upload Conversion Attachment before Converting into Files"},
                            status=status.HTTP_400_BAD_REQUEST)
    sys.path.insert(0, local_path)
    filter_files = Attachments.objects.filter(Feature_Id=feature_id, AttachmentType=attach_type)
    filter_values = filter_files.values_list()
    if filter_values:
        for record in filter_values:
            source_path = record[6]
            source_file = record[5]
            source_file_blob = container_client.list_blobs(name_starts_with=source_path)
            if source_file_blob:
                source_data = ''
                for blob in source_file_blob:
                    source_data = container_client.get_blob_client(blob).download_blob().readall()
                    source_data = source_data.decode()
                a = import_file(local_path)
                function_call = getattr(a, str(feature).strip())
                output = function_call(source_data, schema)
                output_path = 'media/' + migid + '/' + 'Project_V' + str(
                    project_id) + '/' + objtype + '/' + feature + '/' + 'Feature_V' + str(
                    feature_version_Id) + '/' + 'Actualtargetcode' + '/' + source_file
                blob_client = container_client.get_blob_client(blob=output_path)
                blob_client.upload_blob(output, overwrite=True)
                target_object = Attachments(Project_Version_Id=project_id, Feature_Version_Id=feature_version_Id,
                                            AttachmentType='Actualtargetcode', filename=source_file,
                                            Attachment=output_path, Feature_Id_id=feature_id)
                target_object.save()
        for row in Attachments.objects.all().reverse():
            if Attachments.objects.filter(filename=row.filename, AttachmentType=row.AttachmentType,
                                          Feature_Id_id=row.Feature_Id_id).count() > 1:
                row.delete()
        shutil.rmtree(path + '/Modules')
        serializer = ConversionfilesSerializer(filter_files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response("Please Add Source Code Attachment")


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        return Response(user_data, status=status.HTTP_201_CREATED)


class ResendVerifyEmail(generics.GenericAPIView):
    serializer_class = resendemailserializer
    def post(self, request):
        user = request.data
        email = user['email']
        try:
            user = Users.objects.get(email=email)
            if user.is_verified:
                return Response({'msg': 'user is already verified'})
            token = RefreshToken.for_user(user)
            absurl = frontend_url + 'emailverification?' + str(token)
            subject = 'Verify your email'
            html_message = render_to_string('verifys.html', {'url': absurl})
            plain_message = strip_tags(html_message)
            from_email = EMAIL_HOST_USER
            to = user.email
            mail.send_mail(subject, plain_message, from_email,
                           [to], html_message=html_message)
            return Response({'msg': 'The Verification email has been sent Please Confirm'},
                            status=status.HTTP_201_CREATED)
        except:
            return Response({'msg': 'No Such user Please Register'})


class RequestPasswordResetEmail(generics.GenericAPIView):
    serializer_class = Resetpasswordemailserializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        email = request.data['email']
        if Users.objects.filter(email=email).exists():
            user = Users.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            absurl = frontend_url + 'resetpassword?token=' + \
                     str(token) + "?uid=" + uidb64
            subject = 'Forgot Password'
            html_message = render_to_string(
                'forgotpassword.html', {'url': absurl})
            plain_message = strip_tags(html_message)
            from_email = EMAIL_HOST_USER
            to = user.email
            mail.send_mail(subject, plain_message, from_email,
                           [to], html_message=html_message)
            return Response({'msg': 'we have sent you a link to reset your password'},
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'msg': 'No Such user Please Register'})

        return Response({'msg': 'we have sent you a link to reset your password'}, status=status.HTTP_200_OK)


class PasswordTokenCheckAPI(generics.GenericAPIView):
    def get(self, request, uidb64, token):

        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response({'msg': 'Token is not valid, please request a new one'},
                                status=status.HTTP_401_UNAUTHORIZED)

            return Response({'success': True, 'msg': 'credentials valid', 'uidb64': uidb64, 'token': token},
                            status=status.HTTP_200_OK)

        except DjangoUnicodeDecodeError as identifier:
            return Response({'msg': 'Token is not valid, please request a new one'},
                            status=status.HTTP_401_UNAUTHORIZED)


class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'success': True, 'msg': 'Password Reset Success'}, status=status.HTTP_200_OK)


class VerifyEmail(generics.GenericAPIView):
    def get(self, request):
        token = request.GET.get('token')
        token = token.replace('?', '').strip()
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=['HS256'])
            user = Users.objects.get(id=payload['user_id'])
            if not user.is_verified:
                user.is_verified = True
                user.is_active = True
                user.save()
            return Response({'msg': 'Sucessfully Email Confirmed! Please Login'}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError as identifier:
            return Response({'msg': 'Expired Please Resend Email'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.exceptions.DecodeError as identifier:
            return Response({'msg': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class MyObtainTokenPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer


@api_view(['GET'])
def featurelistperuser(request):
    features = Users.objects.filter(username='naga')
    serializer = viewlevelfeatures(features, many=True)
    data = serializer.data
    data1 = data[0]
    data2 = eval(data1['can_view'])
    return Response(data2)


@api_view(['POST'])
def create_tablepage_featuresdata(request):
    Migration_TypeId = request.data['Migration_TypeId']
    Object_Type = request.data['Object_Type']
    Project_Version_Id = request.data['Project_Version_Id']
    feature_names = Feature.objects.filter(Migration_TypeId=Migration_TypeId,Object_Type=Object_Type,Project_Version_Id=Project_Version_Id).values('Feature_Name').distinct()
    features = []
    if feature_names:
        for dict in feature_names:
            features.append(dict['Feature_Name'])
    final_list = []
    if features:
        for feature in features:
            feature_versions = Feature.objects.filter(Feature_Name=feature, Project_Version_Id=Project_Version_Id)
            version_list = []
            if feature_versions:
                for dict1 in feature_versions.values():
                    version_list.append(dict1['Feature_Version_Id'])
                max_version = max(version_list)
                data = Feature.objects.filter(
                    Migration_TypeId=Migration_TypeId, Object_Type=Object_Type, Feature_Name=feature,
                    Feature_Version_Id=max_version, Project_Version_Id=Project_Version_Id)
                serializer = FeatureSerializer(data, many=True)
                final_list.append(serializer.data)
    final_output_list = []
    for final_dict in final_list:
        if final_dict:
            final_output_list.append(final_dict[0])
    return Response(final_output_list)


@api_view(['POST'])
def get_Featurenames(request):
    Migration_TypeId = request.data['Migration_TypeId']
    Object_Type = request.data['Object_Type']
    # Feature_Name = request.data['Feature_Name']
    Project_Version_Id = request.data['Project_Version_Id']
    final_list = []
    if Object_Type == 'ALL':
        features = Feature.objects.filter(Migration_TypeId=Migration_TypeId)
        feature_names = features.values('Feature_Name').distinct()
        features = []
        for dict in feature_names:
            features.append(dict['Feature_Name'])
        for feature in features:
            feature_versions = Feature.objects.filter(Feature_Name=feature)
            version_list = []
            object_list = []
            for dict1 in feature_versions.values():
                version_list.append(dict1['Feature_Version_Id'])
                object_list.append(dict1['Object_Type'])
            object_list = list(set(object_list))
            max_version = max(version_list)
            for object in object_list:
                data = Feature.objects.filter(
                    Migration_TypeId=Migration_TypeId, Object_Type=object, Feature_Name=feature,
                    Feature_Version_Id=max_version)
                serializer = migrationlevelfeatures(data, many=True)
                final_list.append(serializer.data)
    else:
        features = Feature.objects.filter(Project_Version_Id=Project_Version_Id, Migration_TypeId=Migration_TypeId,
                                          Object_Type=Object_Type)
        feature_names = features.values('Feature_Name').distinct()
        features = []
        for dict in feature_names:
            features.append(dict['Feature_Name'])
        for feature in features:
            feature_versions = Feature.objects.filter(Project_Version_Id=Project_Version_Id,
                                                      Migration_TypeId=Migration_TypeId, Object_Type=Object_Type,
                                                      Feature_Name=feature)
            version_list = []
            for dict1 in feature_versions.values():
                version_list.append(dict1['Feature_Version_Id'])
            max_version = max(version_list)
            data = Feature.objects.filter(Project_Version_Id=Project_Version_Id,
                                          Migration_TypeId=Migration_TypeId, Object_Type=Object_Type,
                                          Feature_Name=feature,
                                          Feature_Version_Id=max_version)
            if data:
                serializer = migrationlevelfeatures(data, many=True)
                final_list.append(serializer.data)
    final_output_list = []
    for final_dict in final_list:
        final_output_list.append(final_dict[0])
    return Response(final_output_list, status=status.HTTP_200_OK)


@api_view(['POST'])
def migrationsscreate(request):
    project_id = request.data['Project_Version_Id']
    migration_type = request.data['Migration_TypeId']
    Object_Type = request.data['Object_Type']
    project_version_limit = request.data['Project_Version_limit']
    feature_version_limit = request.data['Feature_Version_Limit']

    serializer = migrationcreateserializer(data=request.data)
    check_obj_type = migrations.objects.filter(Project_Version_Id=project_id, Migration_TypeId=migration_type,
                                               Object_Type=Object_Type.upper())
    if not check_obj_type:
        if Object_Type == '':
            if project_version_limit == '' and feature_version_limit == '':
                if serializer.is_valid():
                    serializer.save(Code=migration_type.replace(' ', '_'), Object_Type=Object_Type.upper(),
                                    Project_Version_limit=3, Feature_Version_Limit=3)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                if serializer.is_valid():
                    serializer.save(Code=migration_type.replace(' ', '_'), Object_Type=Object_Type.upper(),
                                    Project_Version_limit=project_version_limit,
                                    Feature_Version_Limit=feature_version_limit)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            if serializer.is_valid():
                serializer.save(Code=migration_type.replace(' ', '_'), Object_Type=Object_Type.upper(),
                                Project_Version_limit='', Feature_Version_Limit='')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response('Object Type Already Existed')
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def migrationviewlist(request):
    Project_Version_Id = request.data['Project_Version_Id']
    features = migrations.objects.filter(Project_Version_Id=Project_Version_Id).values('Migration_TypeId',
                                                                                       'Code').distinct()
    serializer = migrationviewserializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def objectviewtlist(request):
    Migration_TypeId = request.data['Migration_TypeId']
    Project_Version_Id = request.data['Project_Version_Id']
    features = migrations.objects.filter(Migration_TypeId=Migration_TypeId,
                                         Project_Version_Id=Project_Version_Id).exclude(Object_Type="")
    serializer = objectviewserializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def approvalscreate(request):
    User_Email = request.data['User_Email']
    Object_Type = request.data['Object_Type']
    Feature_Name = request.data['Feature_Name']
    Access_Type = request.data['Access_Type']
    if Approvals.objects.filter(User_Email=User_Email, Object_Type=Object_Type, Feature_Name=Feature_Name,
                                Access_Type=Access_Type).exists():
        return Response("Request Already Sent")
    else:
        serializer = ApprovalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def approvalslist(request):
    Migration_TypeId = request.data['Migration_TypeId']
    Object_Type = request.data['Object_Type']
    email = request.data['User_Email']

    user = Users.objects.get(email=email)
    admin_access = user.admin_migrations
    if admin_access != '':
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)
    else:
        admin_access_dict = {}

    today = date.today()
    week_ago = today - timedelta(days=7)
    final_list = []

    if Migration_TypeId in admin_access_dict.keys():
        if 'ALL' in admin_access_dict[Migration_TypeId]:
            appr_data = Approvals.objects.filter(Migration_TypeId=Migration_TypeId,
                                                 Object_Type__in=(Object_Type, 'ALL'))
        else:
            appr_data = Approvals.objects.filter(Migration_TypeId=Migration_TypeId, Object_Type=Object_Type)

    for dict in appr_data.values():
        created_date = dict['Created_at']
        if created_date > week_ago:
            final_list.append(dict)
    serializer = ApprovalSerializer(final_list, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def userslist(request):
    features = Users.objects.filter(is_verified=True)
    serializer = usersserializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST', 'GET'])
def permissionscreate(request):
    user_Email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    obj_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    access_type = request.data['Access_Type']
    appr_status = request.data['Approval_Status']
    if appr_status == 'Approved':
        if obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'View':
            perm_data = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                   Object_Type=obj_type,
                                                   Access_Type='View').exclude(Feature_Name='ALL')
            if perm_data:
                perm_data.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'Edit':
            perm_data_view = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Access_Type='View')
            if perm_data_view:
                perm_data_view.delete()
            perm_data_edit = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Access_Type='Edit').exclude(
                Feature_Name='ALL')
            if perm_data_edit:
                perm_data_edit.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'ALL':
            perm_data_view = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Access_Type='View')
            if perm_data_view:
                perm_data_view.delete()
            perm_data_edit = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Access_Type='Edit')
            if perm_data_edit:
                perm_data_edit.delete()
            perm_data_all = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                       Object_Type=obj_type, Access_Type='ALL').exclude(
                Feature_Name='ALL')
            if perm_data_all:
                perm_data_all.delete()
        elif obj_type == 'ALL' and access_type == 'View':
            perm_data = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                   Access_Type='View').exclude(Object_Type='ALL', Feature_Name='ALL')
            if perm_data:
                perm_data.delete()
        elif obj_type == 'ALL' and access_type == 'Edit':
            perm_data_view = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Access_Type='View')
            if perm_data_view:
                perm_data_view.delete()
            perm_data_edit = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Access_Type='Edit').exclude(Object_Type='ALL',
                                                                                    Feature_Name='ALL')
            if perm_data_edit:
                perm_data_edit.delete()
        elif obj_type == 'ALL' and access_type == 'ALL':
            perm_data_view = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Access_Type='View')
            if perm_data_view:
                perm_data_view.delete()
            perm_data_edit = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Access_Type='Edit')
            if perm_data_edit:
                perm_data_edit.delete()
            perm_data_all = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                       Access_Type='ALL').exclude(Object_Type='ALL', Feature_Name='ALL')
            if perm_data_all:
                perm_data_all.delete()
        elif access_type == 'Edit':
            perm_data = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                   Object_Type=obj_type,
                                                   Feature_Name=feature_name, Access_Type='View')
            if perm_data:
                perm_data.delete()
        elif access_type == 'ALL':
            perm_data_view = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Feature_Name=feature_name,
                                                        Access_Type='View')
            perm_data_edit = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                        Object_Type=obj_type, Feature_Name=feature_name,
                                                        Access_Type='Edit')
            if perm_data_view:
                perm_data_view.delete()
            if perm_data_edit:
                perm_data_edit.delete()

    perm_record = Permissions.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                             Feature_Name=feature_name, Access_Type=access_type)
    if not perm_record:
        serializer = PermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response("User already has permission")


@api_view(['GET', 'POST'])
def create_check_list(request):
    email = request.data['User_Email']
    mig_type = request.data['Migration_Type']

    mig_data = migrations.objects.filter(Migration_TypeId=mig_type).exclude(Object_Type='')
    object_names = [obj['Object_Type'] for obj in mig_data.values()]

    perm_object_list = []
    perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                           Access_Type='Edit') | Permissions.objects.filter(User_Email=email,
                                                                                            Migration_TypeId=mig_type,
                                                                                            Access_Type='ALL')
    object_data = perm_data.values('Object_Type')
    for dict in object_data:
        perm_object_list.append(dict['Object_Type'])
    perm_object_list = list(set(perm_object_list))

    inter_dict = {}
    final_list = []
    if 'ALL' in perm_object_list:
        for object_name in object_names:
            inter_dict['Label'] = object_name
            inter_dict['Create_Flag'] = 1
            final_list.append(inter_dict.copy())
    else:
        for object_name in object_names:
            if object_name in perm_object_list:
                inter_dict['Label'] = object_name
                inter_dict['Create_Flag'] = 1
                final_list.append(inter_dict.copy())
            else:
                inter_dict['Label'] = object_name
                inter_dict['Create_Flag'] = 0
                final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['POST'])
def migration_user_view(request):
    email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    project_version = request.data['Project_Version_Id']

    user = Users.objects.get(email=email)
    user_is_superuser = user.is_superuser
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)

    mig_data = migrations.objects.filter(Project_Version_Id=project_version, Migration_TypeId=mig_type).exclude(
        Object_Type='')
    object_names = [obj['Object_Type'] for obj in mig_data.values()]

    perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type)
    object_values_list = [obj['Object_Type'] for obj in perm_data.values()]

    label_dict = {}
    final_list = []
    if user_is_superuser == True:
        if mig_type in admin_access_dict.keys():
            if 'ALL' in admin_access_dict[mig_type]:
                for object_name in object_names:
                    inter_list = []
                    label_dict['Label'] = object_name
                    features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                           Migration_TypeId=mig_type, Object_Type=object_name)
                    feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                    if feature_values:
                        for feature_name in feature_values:
                            inter_dict = {}
                            inter_dict["Feature_Name"] = feature_name
                            inter_list.append(inter_dict)
                        label_dict['SubMenu'] = inter_list
                        label_dict['Admin_Flag'] = 1
                        final_list.append(label_dict.copy())
                    else:
                        label_dict['SubMenu'] = []
                        label_dict['Admin_Flag'] = 1
                        final_list.append(label_dict.copy())
            else:
                for object_name in object_names:
                    inter_list = []
                    label_dict['Label'] = object_name
                    if object_name in admin_access_dict[mig_type]:
                        features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                               Migration_TypeId=mig_type, Object_Type=object_name)
                        feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                        if feature_values:
                            for feature_name in feature_values:
                                inter_dict = {}
                                inter_dict["Feature_Name"] = feature_name
                                inter_list.append(inter_dict)
                            label_dict['SubMenu'] = inter_list
                            label_dict['Admin_Flag'] = 1
                            final_list.append(label_dict.copy())
                        else:
                            label_dict['SubMenu'] = []
                            label_dict['Admin_Flag'] = 1
                            final_list.append(label_dict.copy())
                    else:
                        if object_name in object_values_list:
                            perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                                   Object_Type=object_name)
                            feature_names_list = [obj['Feature_Name'] for obj in perm_data.values()]
                            if 'ALL' in feature_names_list:
                                features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                                       Migration_TypeId=mig_type,
                                                                       Object_Type=object_name)
                                feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                                if feature_values:
                                    for feature_name in feature_values:
                                        inter_dict = {}
                                        inter_dict["Feature_Name"] = feature_name
                                        inter_list.append(inter_dict)
                                    label_dict['SubMenu'] = inter_list
                                    label_dict['Admin_Flag'] = 0
                                    final_list.append(label_dict.copy())
                                else:
                                    label_dict['SubMenu'] = []
                                    label_dict['Admin_Flag'] = 0
                                    final_list.append(label_dict.copy())
                            else:
                                for feature_i in feature_names_list:
                                    inter_dict = {}
                                    inter_dict["Feature_Name"] = feature_i
                                    inter_list.append(inter_dict)
                                label_dict['SubMenu'] = inter_list
                                label_dict['Admin_Flag'] = 0
                                final_list.append(label_dict.copy())
                        else:
                            label_dict['SubMenu'] = []
                            label_dict['Admin_Flag'] = 0
                            final_list.append(label_dict.copy())
        else:
            for object_name in object_names:
                inter_list = []
                label_dict['Label'] = object_name
                if object_name in object_values_list:
                    perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                           Object_Type=object_name)
                    feature_names_list = [obj['Feature_Name'] for obj in perm_data.values()]
                    if 'ALL' in feature_names_list:
                        features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                               Migration_TypeId=mig_type,
                                                               Object_Type=object_name)
                        feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                        if feature_values:
                            for feature_name in feature_values:
                                inter_dict = {}
                                inter_dict["Feature_Name"] = feature_name
                                inter_list.append(inter_dict)
                            label_dict['SubMenu'] = inter_list
                            label_dict['Admin_Flag'] = 0
                            final_list.append(label_dict.copy())
                        else:
                            label_dict['SubMenu'] = []
                            label_dict['Admin_Flag'] = 0
                            final_list.append(label_dict.copy())
                    else:
                        for feature_i in feature_names_list:
                            inter_dict = {}
                            inter_dict["Feature_Name"] = feature_i
                            inter_list.append(inter_dict)
                        label_dict['SubMenu'] = inter_list
                        label_dict['Admin_Flag'] = 0
                        final_list.append(label_dict.copy())
                else:
                    label_dict['SubMenu'] = []
                    label_dict['Admin_Flag'] = 0
                    final_list.append(label_dict.copy())
    elif mig_type in admin_access_dict.keys():
        if 'ALL' in admin_access_dict[mig_type]:
            for object_name in object_names:
                inter_list = []
                label_dict['Label'] = object_name
                features_data = Feature.objects.filter(Project_Version_Id=project_version, Migration_TypeId=mig_type,
                                                       Object_Type=object_name)
                feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                if feature_values:
                    for feature_name in feature_values:
                        inter_dict = {}
                        inter_dict["Feature_Name"] = feature_name
                        inter_list.append(inter_dict)
                    label_dict['SubMenu'] = inter_list
                    label_dict['Admin_Flag'] = 1
                    final_list.append(label_dict.copy())
                else:
                    label_dict['SubMenu'] = []
                    label_dict['Admin_Flag'] = 1
                    final_list.append(label_dict.copy())
        else:
            for object_name in object_names:
                inter_list = []
                label_dict['Label'] = object_name
                if object_name in admin_access_dict[mig_type]:
                    features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                           Migration_TypeId=mig_type, Object_Type=object_name)
                    feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                    if feature_values:
                        for feature_name in feature_values:
                            inter_dict = {}
                            inter_dict["Feature_Name"] = feature_name
                            inter_list.append(inter_dict)
                        label_dict['SubMenu'] = inter_list
                        label_dict['Admin_Flag'] = 1
                        final_list.append(label_dict.copy())
                    else:
                        label_dict['SubMenu'] = []
                        label_dict['Admin_Flag'] = 1
                        final_list.append(label_dict.copy())
                else:
                    if 'ALL' in object_values_list:
                        perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                               Object_Type='ALL')
                        feature_names_list = [obj['Feature_Name'] for obj in perm_data.values()]
                        if 'ALL' in feature_names_list:
                            features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                                   Migration_TypeId=mig_type, Object_Type=object_name)
                            feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                            if feature_values:
                                for feature_name in feature_values:
                                    inter_dict = {}
                                    inter_dict["Feature_Name"] = feature_name
                                    inter_list.append(inter_dict)
                                label_dict['SubMenu'] = inter_list
                                label_dict['Admin_Flag'] = 0
                                final_list.append(label_dict.copy())
                            else:
                                label_dict['SubMenu'] = []
                                label_dict['Admin_Flag'] = 0
                                final_list.append(label_dict.copy())
                        else:
                            for feature_i in feature_names_list:
                                inter_dict = {}
                                inter_dict["Feature_Name"] = feature_i
                                inter_list.append(inter_dict)
                            label_dict['SubMenu'] = inter_list
                            label_dict['Admin_Flag'] = 0
                            final_list.append(label_dict.copy())
                    elif object_name in object_values_list:
                        perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                               Object_Type=object_name)
                        feature_names_list = [obj['Feature_Name'] for obj in perm_data.values()]
                        if 'ALL' in feature_names_list:
                            features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                                   Migration_TypeId=mig_type, Object_Type=object_name)
                            feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                            if feature_values:
                                for feature_name in feature_values:
                                    inter_dict = {}
                                    inter_dict["Feature_Name"] = feature_name
                                    inter_list.append(inter_dict)
                                label_dict['SubMenu'] = inter_list
                                label_dict['Admin_Flag'] = 0
                                final_list.append(label_dict.copy())
                            else:
                                label_dict['SubMenu'] = []
                                label_dict['Admin_Flag'] = 0
                                final_list.append(label_dict.copy())
                        else:
                            for feature_i in feature_names_list:
                                inter_dict = {}
                                inter_dict["Feature_Name"] = feature_i
                                inter_list.append(inter_dict)
                            label_dict['SubMenu'] = inter_list
                            label_dict['Admin_Flag'] = 0
                            final_list.append(label_dict.copy())
                    else:
                        label_dict['SubMenu'] = []
                        label_dict['Admin_Flag'] = 0
                        final_list.append(label_dict.copy())
    elif 'ALL' in object_values_list:
        for object_name in object_names:
            inter_list = []
            label_dict['Label'] = object_name
            features_data = Feature.objects.filter(Project_Version_Id=project_version, Migration_TypeId=mig_type,
                                                   Object_Type=object_name)
            feature_values = [obj['Feature_Name'] for obj in features_data.values()]
            if feature_values:
                for feature_name in feature_values:
                    inter_dict = {}
                    inter_dict["Feature_Name"] = feature_name
                    inter_list.append(inter_dict)
                label_dict['SubMenu'] = inter_list
                if len(admin_access_dict) != 0:
                    if mig_type in admin_access_dict.keys():
                        if object_name in admin_access_dict[mig_type]:
                            label_dict['Admin_Flag'] = 1
                        else:
                            label_dict['Admin_Flag'] = 0
                else:
                    label_dict['Admin_Flag'] = 0
                final_list.append(label_dict.copy())
            else:
                label_dict['SubMenu'] = []
                if len(admin_access_dict) != 0:
                    if mig_type in admin_access_dict.keys():
                        if object_name in admin_access_dict[mig_type]:
                            label_dict['Admin_Flag'] = 1
                        else:
                            label_dict['Admin_Flag'] = 0
                else:
                    label_dict['Admin_Flag'] = 0
                final_list.append(label_dict.copy())
    else:
        for object_name in object_names:
            inter_list = []
            label_dict['Label'] = object_name
            if object_name in object_values_list:
                perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type,
                                                       Object_Type=object_name)
                feature_names_list = [obj['Feature_Name'] for obj in perm_data.values()]
                if 'ALL' in feature_names_list:
                    features_data = Feature.objects.filter(Project_Version_Id=project_version,
                                                           Migration_TypeId=mig_type, Object_Type=object_name)
                    feature_values = [obj['Feature_Name'] for obj in features_data.values()]
                    if feature_values:
                        for feature_name in feature_values:
                            inter_dict = {}
                            inter_dict["Feature_Name"] = feature_name
                            inter_list.append(inter_dict)
                        label_dict['SubMenu'] = inter_list
                        label_dict['Admin_Flag'] = 0
                        final_list.append(label_dict.copy())
                    else:
                        label_dict['SubMenu'] = []
                        label_dict['Admin_Flag'] = 0
                        final_list.append(label_dict.copy())
                else:
                    for feature_i in feature_names_list:
                        inter_dict = {}
                        inter_dict["Feature_Name"] = feature_i
                        inter_list.append(inter_dict)
                    label_dict['SubMenu'] = inter_list
                    label_dict['Admin_Flag'] = 0
                    final_list.append(label_dict.copy())
            else:
                label_dict['SubMenu'] = []
                label_dict['Admin_Flag'] = 0
                final_list.append(label_dict.copy())
    for final_dict in final_list:
        submenu_list = final_dict['SubMenu']
        submenu_list_new = [i for n, i in enumerate(submenu_list) if i not in submenu_list[n + 1:]]
        final_dict['SubMenu'] = submenu_list_new
    return Response(final_list)


@api_view(['PUT'])
def approvalsupdate(request, id):
    user_Email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    obj_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    access_type = request.data['Access_Type']
    appr_status = request.data['Approval_Status']
    feature = Approvals.objects.get(id=id)
    serializer = ApprovalSerializer(instance=feature, data=request.data)

    if appr_status == 'Approved':
        if obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'View':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                                Access_Type='View').exclude(Feature_Name='ALL')
            if app_data:
                app_data.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'Edit':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='Edit').exclude(Feature_Name='ALL')
            if app_data_edit:
                app_data_edit.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='Edit')
            if app_data_edit:
                app_data_edit.delete()
            app_data_all = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                    Object_Type=obj_type,
                                                    Access_Type='ALL').exclude(Feature_Name='ALL')
            if app_data_all:
                app_data_all.delete()
        elif obj_type == 'ALL' and access_type == 'View':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                Access_Type='View').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data:
                app_data.delete()
        elif obj_type == 'ALL' and access_type == 'Edit':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='Edit').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data_edit:
                app_data_edit.delete()
        elif obj_type == 'ALL' and access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='Edit')
            if app_data_edit:
                app_data_edit.delete()
            app_data_all = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                    Access_Type='ALL').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data_all:
                app_data_all.delete()
        elif access_type == 'Edit':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                                Feature_Name=feature_name, Access_Type='View')
            if app_data:
                app_data.delete()
        elif access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Feature_Name=feature_name, Access_Type='View')
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Feature_Name=feature_name, Access_Type='Edit')
            if app_data_view:
                app_data_view.delete()
            if app_data_edit:
                app_data_edit.delete()
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def admin_permissions(request):
    email = request.data['email']
    migtype = request.data['mig_type']
    object_type = request.data['Object_Type']
    user = Users.objects.get(email=email)
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        final_dict = {}
        object_list = []
        object_list.append(object_type)
        final_dict[migtype] = object_list
        a = Users.objects.get(email=email)
        a.admin_migrations = final_dict
        a.save()
        return Response("Admin access created for user")
    else:
        admin_access = user.admin_migrations.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)
        if migtype not in admin_access_dict.keys():
            object_list = []
            object_list.append(object_type)
            admin_access_dict[migtype] = object_list
            a = Users.objects.get(email=email)
            a.admin_migrations = admin_access_dict
            a.save()
            return Response("Admin access created for user")
        else:
            if object_type not in admin_access_dict[migtype]:
                if object_type == 'ALL':
                    admin_access_dict[migtype].clear()
                    admin_access_dict[migtype].append(object_type)
                    a = Users.objects.get(email=email)
                    a.admin_migrations = admin_access_dict
                    a.save()
                    return Response("Admin access created for user")
                else:
                    if 'ALL' not in admin_access_dict[migtype]:
                        admin_access_dict[migtype].append(object_type)
                        a = Users.objects.get(email=email)
                        a.admin_migrations = admin_access_dict
                        a.save()
                        return Response("Admin access created for user")
                    else:
                        return Response("User already has admin permission for ALL Object Types")

            else:
                return Response("User already has this admin permission")


@api_view(['GET', 'POST', 'PUT'])
def remove_admin_permission(request):
    User_Email = request.data['User_Email']
    mig_type = request.data['Migration_Type']
    object_type = request.data['Object_type']
    user = Users.objects.get(email=User_Email)
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        user.admin_migrations = ''
        user.save()
        return Response("No Permissions")
    else:
        admin_access = user.admin_migrations.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)
        if mig_type in admin_access_dict.keys():
            if object_type == 'ALL':
                del admin_access_dict[mig_type]
                if len(admin_access_dict) == 0:
                    a = Users.objects.get(email=User_Email)
                    a.admin_migrations = ''
                    a.save()
                else:
                    a = Users.objects.get(email=User_Email)
                    a.admin_migrations = admin_access_dict
                    a.save()
            else:
                if object_type in admin_access_dict[mig_type]:
                    admin_access_dict[mig_type].remove(object_type)
                    if admin_access_dict[mig_type]:
                        a = Users.objects.get(email=User_Email)
                        a.admin_migrations = admin_access_dict
                        a.save()
                    else:
                        del admin_access_dict[mig_type]
                        if len(admin_access_dict) == 0:
                            a = Users.objects.get(email=User_Email)
                            a.admin_migrations = ''
                            a.save()
                        else:
                            a = Users.objects.get(email=User_Email)
                            a.admin_migrations = admin_access_dict
                            a.save()
        return Response("Admin access removed")


@api_view(['GET', 'POST'])
def admin_rm_migration_list(request):
    final_list = []
    inter_dict = {}
    User_Email = request.data['User_Email']
    user = Users.objects.get(email=User_Email)
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)
    for migration in admin_access_dict.keys():
        inter_dict['Migration_Type'] = migration
        final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['GET', 'POST'])
def admin_rm_object_list(request):
    final_list = []
    inter_dict = {}
    User_Email = request.data['User_Email']
    mig_type = request.data['Migration_Type']

    user = Users.objects.get(email=User_Email)
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)
    if mig_type in admin_access_dict.keys():
        object_list = admin_access_dict[mig_type]
        for object_i in object_list:
            inter_dict['Object_type'] = object_i
            final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['PUT'])
def permissionsupdate(request, User_Email):
    feature = Permissions.objects.get(User_Email=User_Email)
    serializer = PermissionSerializer(instance=feature, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def permissionslist(request):
    if len(request.data) > 2:
        Object_Type = request.data['Object_Type']
        User_Email = request.data['User_Email']
        Migration_TypeId = request.data['Migration_TypeId']
        if Object_Type == '' or Object_Type == None:
            features = Permissions.objects.filter(User_Email=User_Email, Migration_TypeId=Migration_TypeId)
        else:
            features = Permissions.objects.filter(User_Email=User_Email, Migration_TypeId=Migration_TypeId,
                                                  Object_Type=Object_Type)
    elif len(request.data) > 1:
        User_Email = request.data['User_Email']
        Migration_TypeId = request.data['Migration_TypeId']
        features = Permissions.objects.filter(User_Email=User_Email, Migration_TypeId=Migration_TypeId)
    else:
        Migration_TypeId = request.data['Migration_TypeId']
        features = Permissions.objects.filter(Migration_TypeId=Migration_TypeId)
    serializer = PermissionSerializer(features, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def admin_users_list(request):
    users = Users.objects.all()
    final_list = []
    inter_dict = {}
    for user_i in users.values():
        admin_mig_value = user_i['admin_migrations']
        if admin_mig_value == '' or admin_mig_value == None:
            continue
        else:
            inter_dict['Email'] = user_i['email']
            admin_access = admin_mig_value.replace("\'", "\"")
            admin_access_dict = json.loads(admin_access)
            migration_type_list = admin_access_dict.keys()
            for migration in migration_type_list:
                inter_dict['Migration_Type'] = migration
                inter_dict['Object_types'] = admin_access_dict[migration]
                final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['GET'])
def super_users_list(request):
    users = Users.objects.all()
    superuser_list = []
    superuser_dict = {}
    for user_i in users.values():
        if user_i['is_superuser'] == True:
            superuser_dict['User_Name'] = user_i['username']
            superuser_dict['Email'] = user_i['email']
            superuser_list.append(superuser_dict.copy())
    return Response(superuser_list)


@api_view(['POST'])
def grant_access_approve(request):
    user_Email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    obj_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    access_type = request.data['Access_Type']
    appr_status = request.data['Approval_Status']
    if appr_status == 'Approved':
        if obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'View':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                                Access_Type='View').exclude(Feature_Name='ALL')
            if app_data:
                app_data.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'Edit':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='Edit').exclude(Feature_Name='ALL')
            if app_data_edit:
                app_data_edit.delete()
        elif obj_type != 'ALL' and feature_name == 'ALL' and access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Access_Type='Edit')
            if app_data_edit:
                app_data_edit.delete()
            app_data_all = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                    Object_Type=obj_type,
                                                    Access_Type='ALL').exclude(Feature_Name='ALL')
            if app_data_all:
                app_data_all.delete()
        elif obj_type == 'ALL' and access_type == 'View':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                Access_Type='View').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data:
                app_data.delete()
        elif obj_type == 'ALL' and access_type == 'Edit':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='Edit').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data_edit:
                app_data_edit.delete()
        elif obj_type == 'ALL' and access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='View')
            if app_data_view:
                app_data_view.delete()
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Access_Type='Edit')
            if app_data_edit:
                app_data_edit.delete()
            app_data_all = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                    Access_Type='ALL').exclude(Object_Type='ALL', Feature_Name='ALL')
            if app_data_all:
                app_data_all.delete()
        elif access_type == 'Edit':
            app_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                                Feature_Name=feature_name, Access_Type='View')
            if app_data:
                app_data.delete()
        elif access_type == 'ALL':
            app_data_view = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Feature_Name=feature_name, Access_Type='View')
            app_data_edit = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type,
                                                     Object_Type=obj_type,
                                                     Feature_Name=feature_name, Access_Type='Edit')
            if app_data_view:
                app_data_view.delete()
            if app_data_edit:
                app_data_edit.delete()

    appr_data = Approvals.objects.filter(User_Email=user_Email, Migration_TypeId=mig_type, Object_Type=obj_type,
                                         Feature_Name=feature_name,
                                         Access_Type=access_type)
    if appr_data:
        data_appr_status = appr_data.values()[0]['Approval_Status']
        if data_appr_status == 'Approved':
            serializer = ApprovalSerializer(appr_data, many=True)
            return Response(serializer.data[0])
        elif data_appr_status == 'Pending':
            approval_record = Approvals.objects.get(User_Email=user_Email, Migration_TypeId=mig_type,
                                                    Object_Type=obj_type, Feature_Name=feature_name,
                                                    Access_Type=access_type)
            serializer = ApprovalSerializer(instance=approval_record, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        serializer = ApprovalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def createsuperadmin(request):
    email = request.data['email']
    features = Users.objects.get(email=email)
    features.is_superuser = True
    features.is_verified = True
    features.save()
    return Response('super admin created successfully')


@api_view(['GET', 'POST'])
def migrationlistperuser(request):
    email = request.data['email']
    project_version_mig_types = migrations.objects.values(
        'Migration_TypeId').distinct()

    user = Users.objects.get(email=email)
    user_mig_access = user.user_migrations

    if user_mig_access == '' or user_mig_access == None:
        user_mig_types_list = []
    else:
        user_mig_types_list = user_mig_access.split(',')
        user_mig_types_list = [x for x in user_mig_types_list if x != '']
    final_list = []
    interdict = {}
    for mig_type in project_version_mig_types:
        if mig_type['Migration_TypeId'] in user_mig_types_list:
            interdict['title'] = mig_type['Migration_TypeId']
            final_list.append(interdict.copy())
    return Response(final_list)


@api_view(['GET'])
def pdf_download(request):
    file_path = 'Documents/PDF/instructions.pdf'
    file_name = 'instructions.pdf'
    fl = open(file_path, 'rb')
    mime_type, _ = mimetypes.guess_type(file_path)
    response = HttpResponse(fl, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % file_name
    return response


@api_view(['GET'])
def template_download(request):
    file_path = 'Documents/Template/template.py'
    file_name = 'template.py'
    fl = open(file_path, 'rb')
    mime_type, _ = mimetypes.guess_type(file_path)
    response = HttpResponse(fl, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % file_name
    return response


@api_view(['POST'])
def objectadminviewtlist(request):
    Migration_TypeId = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']
    email = request.data['User_Email']

    user = Users.objects.get(email=email)
    admin_access = user.admin_migrations
    if admin_access == '' or admin_access == None:
        admin_access_dict = {}
    else:
        admin_access = admin_access.replace("\'", "\"")
        admin_access_dict = json.loads(admin_access)

    object_list = []
    final_list = []
    inter_dict = {}

    if Migration_TypeId in admin_access_dict.keys():
        if 'ALL' in admin_access_dict[Migration_TypeId]:
            object_list.append('ALL')
            object_list.append(object_type)
        else:
            object_list.append(object_type)
    for obj in object_list:
        inter_dict['Object_Type'] = obj
        final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['POST'])
def feature_approval_list(request):
    project_version = request.data['Project_Version_Id']
    migration_type = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']

    today = date.today()
    week_ago = today - timedelta(days=7)
    final_list = []
    feature_data = Feature.objects.filter(Project_Version_Id=project_version, Migration_TypeId=migration_type,
                                          Object_Type=object_type,
                                          Feature_version_approval_status__in=(
                                              'Approved', 'Awaiting Approval', 'Denied'))
    for dict in feature_data.values():
        Request_Create_Date = dict['Feature_Approval_Date']
        if Request_Create_Date > week_ago:
            final_list.append(dict)
    serializer = FeatureSerializer(feature_data, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def approval_featurecreate(request):
    migration_type = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    project_version = request.data['Project_Version_Id']

    migration_data = migrations.objects.filter(Project_Version_Id=project_version, Migration_TypeId=migration_type,
                                               Object_Type='')
    feature_version_limit = migration_data.values()[0]['Feature_Version_Limit']
    n = int(feature_version_limit)

    mig_versions_data = migrations.objects.filter(Migration_TypeId=migration_type).values('Project_Version_Id')
    project_versions_list = []
    for dict in mig_versions_data:
        project_versions_list.append(dict['Project_Version_Id'])
    project_versions_list = list(set(project_versions_list))
    max_project_version = max(project_versions_list)

    feature_versions_list_all = []
    feature_latest_versions_list = []
    for project_version_i in project_versions_list:
        mig_feature_versions_data = Feature.objects.filter(Project_Version_Id=project_version_i,
                                                           Object_Type=object_type,
                                                           Migration_TypeId=migration_type,
                                                           Feature_Name=feature_name).values('Feature_Version_Id')
        f_versions_list_without_prefix = []
        if mig_feature_versions_data:
            for dict in mig_feature_versions_data:
                f_versions_list_without_prefix.append(dict['Feature_Version_Id'])
            if project_version_i != project_version:
                max_in_f_versions_list_without_prefix = max(f_versions_list_without_prefix)
                feature_latest_versions_list.append(
                    str(project_version_i) + '.' + str(max_in_f_versions_list_without_prefix))
            for f_version in f_versions_list_without_prefix:
                feature_versions_list_all.append(str(project_version_i) + '.' + str(f_version))
    feature_data = Feature.objects.filter(Migration_TypeId=migration_type, Object_Type=object_type,
                                          Feature_Name=feature_name, Project_Version_Id=project_version,
                                          Feature_version_approval_status='Approved')
    version_list = []
    if feature_data:
        for dict in feature_data.values():
            version_list.append(dict['Feature_Version_Id'])
        max_version = max(version_list)
        serializer = FeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(Feature_Version_Id=max_version + 1)
            max_feature = Feature.objects.get(Migration_TypeId=migration_type, Object_Type=object_type,
                                              Feature_Name=feature_name,
                                              Project_Version_Id=project_version,
                                              Feature_Version_Id=max_version)
            max_feature_id = max_feature.Feature_Id
            max_feature_attachments_data = Attachments.objects.filter(Feature_Id_id=max_feature_id)
            creating_feature_version = Feature.objects.get(Migration_TypeId=migration_type, Object_Type=object_type,
                                                           Feature_Name=feature_name,
                                                           Project_Version_Id=project_version,
                                                           Feature_Version_Id=max_version + 1)
            creating_version_feature_id = creating_feature_version.Feature_Id

            for dict in max_feature_attachments_data.values():
                att_object2 = Attachments(Project_Version_Id=dict['Project_Version_Id'],
                                          Feature_Version_Id=max_version + 1,
                                          AttachmentType=dict['AttachmentType'], filename=dict['filename'],
                                          Attachment=dict['Attachment'],
                                          Feature_Id_id=creating_version_feature_id)
                att_object2.save()
            latest_version_source = 'media/' + migration_type + '/' + 'Project_V' + str(
                project_version) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(
                max_version) + '/'
            sas_token = generate_account_sas(account_name=account_name, account_key=account_key,
                                             resource_types=ResourceTypes(
                                                 service=True, container=True, object=True),
                                             permission=AccountSasPermissions(read=True),
                                             expiry=datetime.utcnow() + timedelta(hours=1))
            source_blob_service_client = BlobServiceClient(
                account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
            des_blob_service_client = BlobServiceClient(
                account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)

            source_container_client = source_blob_service_client.get_container_client(container_name_var)
            blob_list = source_container_client.list_blobs(name_starts_with=latest_version_source)
            if blob_list:
                for blob in blob_list:
                    source_blob = source_container_client.get_blob_client(blob)
                    source_url = source_blob.url + '?' + sas_token
                    des_blob_service_client.get_blob_client(
                        container_name_var, source_blob.blob_name.replace('Feature_V' + str(max_version),'Feature_V' + str(max_version + 1))).start_copy_from_url(source_url)

            version_list.append(int(max_version + 1))
            feature_versions_list_all.append(str(project_version) + '.' + str(max_version + 1))
            feature_versions_list_all = sorted(feature_versions_list_all, key=float)
            if len(feature_versions_list_all) > int(feature_version_limit):
                version_list_del = feature_versions_list_all[:-n or None]
                for version in version_list_del:
                    min_version = version
                    if min_version not in feature_latest_versions_list:
                        del_feature_version = min_version.split('.')[1]
                        del_project_version = min_version.split('.')[0]
                        min_feature = Feature.objects.get(Migration_TypeId=migration_type, Object_Type=object_type,
                                                          Feature_Name=feature_name,
                                                          Project_Version_Id=del_project_version,
                                                          Feature_Version_Id=del_feature_version)
                        feature_id = min_feature.Feature_Id
                        min_feature.delete()
                        attachments_data = Attachments.objects.filter(Feature_Id_id=feature_id)
                        attachments_data.delete()
                        folder_path = 'media/' + migration_type + '/' + 'Project_V' + str(
                            del_project_version) + '/' + object_type + '/' + feature_name + '/' + 'Feature_V' + str(
                            del_feature_version)
                        del_blobs = source_container_client.list_blobs(name_starts_with=folder_path)
                        if del_blobs:
                            for blob in del_blobs:
                                source_container_client.delete_blobs(blob)
            for row in Feature.objects.all().reverse():
                if Feature.objects.filter(Migration_TypeId=row.Migration_TypeId,Object_Type = row.Object_Type, Feature_Name=row.Feature_Name,
                                          Project_Version_Id=row.Project_Version_Id,
                                          Feature_Version_Id=row.Feature_Version_Id).count() > 1:
                    row.delete()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response("New versions won't be created until it has a previous version approved")


@api_view(['GET', 'POST'])
def project_versions_list(request):
    migration_type = request.data['Migration_TypeId']
    project_versions = migrations.objects.filter(Migration_TypeId=migration_type).values(
        'Project_Version_Id').distinct()
    final_list = []
    version_list = []
    if project_versions:
        for dict in project_versions:
            version_list.append(dict['Project_Version_Id'])
        inter_dict = {}
        version_list = [i for i in version_list if i != 'null']
        for i in version_list:
            inter_dict['title'] = 'V' + str(i)
            inter_dict['code'] = int(i)
            final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['POST'])
def create_project_version(request):
    migration = request.data['Migration_TypeId']
    mig_data = migrations.objects.filter(Migration_TypeId=migration, Object_Type='').values('Project_Version_Id')
    mig_project_versions_list = [dict['Project_Version_Id'] for dict in mig_data if dict['Project_Version_Id'] != '']
    max_value = max(mig_project_versions_list)
    prev_project_version = max_value
    current_project_version = int(max_value) + 1

    object_types_old = migrations.objects.filter(Project_Version_Id=prev_project_version,
                                                 Migration_TypeId=migration).values('Object_Type').distinct()
    object_types_old_list = [dict['Object_Type'] for dict in object_types_old if dict['Object_Type'] != '']

    project_version_limit = migrations.objects.filter(Migration_TypeId=migration, Object_Type='').values()[0][
        'Project_Version_limit']
    n = int(project_version_limit)

    project_versions_list = []
    mig_copy_data = migrations.objects.filter(Migration_TypeId=migration)
    project_versions = mig_copy_data.values('Project_Version_Id')
    for i in project_versions:
        project_versions_list.append(int(i['Project_Version_Id']))
    project_versions_list = list(set(project_versions_list))
    max_version = max(project_versions_list)
    project_versions_list.append(int(max_version + 1))

    mig_copy_project_version_data = migrations.objects.filter(Project_Version_Id=prev_project_version,
                                                              Migration_TypeId=migration)

    for dict in mig_copy_project_version_data.values():
        migrations.objects.create(Project_Version_Id=current_project_version,
                                  Migration_TypeId=dict['Migration_TypeId'],
                                  Object_Type=dict['Object_Type'], Code=dict['Code'],
                                  Project_Version_limit=dict['Project_Version_limit'],
                                  Feature_Version_Limit=dict['Feature_Version_Limit'])
    container_client = azure_connection()
    if len(project_versions_list) > int(project_version_limit):
        project_versions_list_del = project_versions_list[:-n or None]
        for version in project_versions_list_del:
            mig_del_data = migrations.objects.filter(Project_Version_Id=int(version), Migration_TypeId=migration)
            mig_del_data.delete()

            feature_del_data = Feature.objects.filter(Project_Version_Id=int(version), Migration_TypeId=migration)
            feature_del_data.delete()

            attachments_del_data = Attachments.objects.filter(Project_Version_Id=int(version),
                                                              Attachment__contains=str(migration))
            attachments_del_data.delete()
            folder_path_del = 'media/' + migration + '/' + 'Project_V' + str(version)
            del_blobs = container_client.list_blobs(name_starts_with=folder_path_del)
            if del_blobs:
                for blob in del_blobs:
                    container_client.delete_blobs(blob)

    for object_i in object_types_old_list:
        feature_names_old = Feature.objects.filter(Project_Version_Id=prev_project_version,
                                                   Migration_TypeId=migration, Object_Type=object_i).values(
            'Feature_Name').distinct()
        feature_names_old_list = [dict['Feature_Name'] for dict in feature_names_old if dict['Feature_Name'] != '']

        for feature in feature_names_old_list:
            feature_versions_old = Feature.objects.filter(Project_Version_Id=prev_project_version,
                                                          Migration_TypeId=migration,
                                                          Object_Type=object_i, Feature_Name=feature).values(
                'Feature_Version_Id').distinct()
            feature_versions_old_list = [dict['Feature_Version_Id'] for dict in feature_versions_old if
                                         dict['Feature_Version_Id'] != '']
            if feature_versions_old_list:
                latest_version = max(feature_versions_old_list)

                feature_data2 = Feature.objects.filter(Project_Version_Id=prev_project_version,
                                                       Migration_TypeId=migration, Object_Type=object_i,
                                                       Feature_Name=feature,
                                                       Feature_Version_Id=latest_version).last()
                attachment_feature_id_progress_old = feature_data2.Feature_Id

                feature_data2.Feature_Id = None
                feature_data2.Project_Version_Id = current_project_version
                feature_data2.Feature_Version_Id = 1
                feature_data2.Feature_Approval_Date = None
                feature_data2.save()

                latest_version_source = 'media/' + migration + '/' + 'Project_V' + str(
                    prev_project_version) + '/' + object_i + '/' + feature + '/' + 'Feature_V' + str(
                    latest_version) + '/'
                sas_token = generate_account_sas(account_name=account_name, account_key=account_key,
                                                 resource_types=ResourceTypes(
                                                 service=True, container=True, object=True),
                                                 permission=AccountSasPermissions(read=True),
                                                 expiry=datetime.utcnow() + timedelta(hours=1))
                source_blob_service_client = BlobServiceClient(
                    account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
                des_blob_service_client = BlobServiceClient(
                    account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
                source_container_client = source_blob_service_client.get_container_client(container_name_var)
                blob_list = source_container_client.list_blobs(name_starts_with=latest_version_source)
                if blob_list:
                    for blob in blob_list:
                        source_blob = source_container_client.get_blob_client(blob)
                        source_url = source_blob.url + '?' + sas_token
                        source_blob.blob_name = source_blob.blob_name.replace('Project_V' + str(prev_project_version),
                                                      'Project_V' + str(current_project_version))
                        source_blob.blob_name = source_blob.blob_name.replace('Feature_V' + str(latest_version), 'Feature_V1')
                        des_blob_service_client.get_blob_client(
                            container_name_var, source_blob.blob_name).start_copy_from_url(source_url)

                feature_data_progress = Feature.objects.filter(Project_Version_Id=current_project_version,
                                                               Migration_TypeId=migration, Object_Type=object_i,
                                                               Feature_Name=feature,
                                                               Feature_Version_Id=1)
                attachment_feature_id_progress_new = feature_data_progress[0].Feature_Id

                attachment_data_progress = Attachments.objects.filter(
                    Feature_Id_id=attachment_feature_id_progress_old)
                for dict in attachment_data_progress.values():
                    att_type = dict['AttachmentType']
                    filename = dict['filename']
                    feature_version_id = 1
                    attachment = dict['Attachment']
                    attachment = attachment.replace('Project_V' + str(prev_project_version),
                                                    'Project_V' + str(current_project_version))
                    att_object2 = Attachments(Project_Version_Id=current_project_version,
                                              Feature_Version_Id=feature_version_id,
                                              AttachmentType=att_type, filename=filename,
                                              Attachment=attachment,
                                              Feature_Id_id=attachment_feature_id_progress_new)
                    att_object2.save()

                if len(feature_versions_old_list) > 1:
                    version_del = max(feature_versions_old_list)
                    del_feature = Feature.objects.get(Migration_TypeId=migration, Object_Type=object_i,
                                                      Feature_Name=feature, Project_Version_Id=prev_project_version,
                                                      Feature_Version_Id=version_del)
                    feature_id = del_feature.Feature_Id
                    del_feature.delete()
                    attachments_data = Attachments.objects.filter(Feature_Id_id=feature_id)
                    attachments_data.delete()
                    folder_path = 'media/' + migration + '/' + 'Project_V' + str(
                        prev_project_version) + '/' + object_i + '/' + feature + '/' + 'Feature_V' + str(
                        version_del)
                    del_blobs = container_client.list_blobs(name_starts_with=folder_path)
                    if del_blobs:
                        for blob in del_blobs:
                            source_container_client.delete_blobs(blob)
    return Response("New Project Version Created Successfully")

@api_view(['POST'])
def create_user_admin(request):
    email = request.data['email']
    user_object = Users.objects.get(email=email)
    user_object.is_user_admin = True
    user_object.save()
    return Response('user admin created successfully')


@api_view(['POST'])
def user_admin_permissions(request):
    email = request.data['email']
    migtype = request.data['mig_type']
    user = Users.objects.get(email=email)
    user_admin_access = user.user_migrations
    if user_admin_access == '' or user_admin_access == None:
        access_str = ''
        access_str = access_str + migtype + ','
        a = Users.objects.get(email=email)
        a.user_migrations = access_str
        a.save()
        return Response("user admin access created for user")
    else:
        user_admin_access_list = user_admin_access.split(',')
        if migtype not in user_admin_access_list:
            user_admin_access = user_admin_access + migtype + ','
            a = Users.objects.get(email=email)
            a.user_migrations = user_admin_access
            a.save()
            return Response("user admin access created for user")
        return Response("user already have user admin access created for user")


@api_view(['GET'])
def useradminlist(request):
    features = Users.objects.filter(is_user_admin=True)
    serializer = useradminlistserializer(features, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def removeuseradmin(request):
    email = request.data['email']
    features = Users.objects.get(email=email)
    features.is_user_admin = False
    features.save()
    return Response('User admin removed successfully')


@api_view(['POST'])
def removesuperadmin(request):
    email = request.data['email']
    user_object = Users.objects.get(email=email)
    super_user_list = Users.objects.filter(is_superuser=True)
    if len(super_user_list) > 2:
        user_object.is_superuser = False
        user_object.save()
        return Response('super admin removed successfully')
    else:
        return Response('Super admin cannot be deleted as number of super admin users less than 2')


@api_view(['GET'])
def user_waiting_list(request):
    users = Users.objects.all()
    final_list = []
    inter_dict = {}
    for user_i in users.values():
        user_mig_value = user_i['user_migrations']
        user_registration_status = user_i['user_registration_status']
        inter_dict['Email'] = user_i['email']
        inter_dict['MigrationTypes'] = user_mig_value
        inter_dict['Status'] = user_registration_status
        final_list.append(inter_dict.copy())
    return Response(final_list)


@api_view(['GET'])
def userslist_useradminpage(request):
    user_object = Users.objects.filter(user_registration_status__in=('Awaiting for admin approval', 'Confirmed'))
    serializer = usersserializer(user_object, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def migrationlist_useradmin(request):
    mig_objects = migrations.objects.values('Migration_TypeId').distinct()
    serializer = migrationuseradminserializer(mig_objects, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def user_admin_actions(request):
    email = request.data['email']
    user_registration_status = request.data['user_registration_status']
    user_object = Users.objects.get(email=email)
    if user_registration_status == 'Confirmed':
        user_object.user_registration_status = user_registration_status
        user_object.save()

        token = RefreshToken.for_user(user_object)
        absurl = frontend_url + 'emailverification?' + str(token)
        subject = 'Verify your email'
        html_message = render_to_string('verifys.html', {'url': absurl})
        plain_message = strip_tags(html_message)
        from_email = EMAIL_HOST_USER
        to = user_object.email

        mail.send_mail(subject, plain_message, from_email,
                       [to], html_message=html_message)
        return Response('User confirmation successful and Email has been sent to user to verify email')
    else:
        user_object.user_registration_status = user_registration_status
        user_object.save()
        return Response('User has been rejected')

def file_share_copy():
    connect_str = fileshare_connectionString
    container_name = container_name_var
    local_path = 'Conversion_Modules'
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container_name)
    myblobs = container_client.list_blobs(name_starts_with='Conversion_Modules')
    if myblobs:
        for blob in myblobs:
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            container_client.delete_blob(blob)
    for r, d, f in os.walk(local_path):
        if f:
            for file in f:
                file_path_on_azure = os.path.join(r, file)
                file_path_on_local = os.path.join(r, file)
                blob_service_client = BlobServiceClient.from_connection_string(connect_str)
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path_on_azure)
                with open(file_path_on_local, "rb") as data:
                    blob_client.upload_blob(data)


@api_view(['GET'])
def delete_folders_fromfileshare(request):
    connect_str = fileshare_connectionString
    container_name = container_name_var
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container_name)
    myblobs = container_client.list_blobs()
    if myblobs:
        for blob in myblobs:
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            container_client = blob_service_client.get_container_client(container_name)
            container_client.delete_blob(blob)
    return Response("Conversion Modules,Media and Modules folders are deleted from azure fileshare successfully")


@api_view(['GET'])
def export_to_fileshare(request):
    connect_str = fileshare_connectionString
    container_name = container_name_var
    local_path_media = 'media'
    local_path_module = 'Modules'
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container_name)
    myblobs_media = container_client.list_blobs(name_starts_with='media')
    if myblobs_media:
        for blob in myblobs_media:
            container_client.delete_blob(blob)
    for r, d, f in os.walk(local_path_media):
        if f:
            for file in f:
                file_path_on_azure = os.path.join(r, file)
                file_path_on_local = os.path.join(r, file)
                blob_service_client = BlobServiceClient.from_connection_string(connect_str)
                container_client = blob_service_client.get_container_client(container_name)
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path_on_azure)
                with open(file_path_on_local, "rb") as data:
                    blob_client.upload_blob(data)
    myblobs_module = container_client.list_blobs(name_starts_with='Modules')
    if myblobs_module:
        for blob in myblobs_module:
            container_client.delete_blob(blob)
    for r, d, f in os.walk(local_path_module):
        if f:
            for file in f:
                file_path_on_azure = os.path.join(r, file)
                file_path_on_local = os.path.join(r, file)
                blob_service_client = BlobServiceClient.from_connection_string(connect_str)
                container_client = blob_service_client.get_container_client(container_name)
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_path_on_azure)
                with open(file_path_on_local, "rb") as data:
                    blob_client.upload_blob(data)
    return Response("Folders exported successfully to azure fileshare")


@api_view(['GET', 'POST'])
def migration_type_creation_based_on_old(request):
    old_migration_type = request.data['Migration_TypeId']
    new_migration_type = request.data['New_Migration_Type']

    mig_data_old = migrations.objects.filter(Migration_TypeId=old_migration_type)
    for dict in mig_data_old.values():
        migrations.objects.create(Project_Version_Id=dict['Project_Version_Id'],
                                  Migration_TypeId=new_migration_type,
                                  Object_Type=dict['Object_Type'], Code=new_migration_type.replace(' ', '_'),
                                  Project_Version_limit=dict['Project_Version_limit'],
                                  Feature_Version_Limit=dict['Feature_Version_Limit'])
    features_data_old = Feature.objects.filter(Migration_TypeId=old_migration_type)
    for dict in features_data_old.values():
        Feature.objects.create(Migration_TypeId=new_migration_type, Feature_Id=None,
                               Project_Version_Id=dict['Project_Version_Id'],
                               Feature_Version_Id=dict['Feature_Version_Id'],
                               Object_Type=dict['Object_Type'], Feature_Name=dict['Feature_Name'],
                               Feature_version_approval_status=dict['Feature_version_approval_status'],
                               Level=dict['Level'], Keywords=dict['Keywords'], Estimations=dict['Estimations'],
                               Sequence=dict['Sequence'], Source_FeatureDescription=dict['Source_FeatureDescription'],
                               Source_Code=dict['Source_Code'], Conversion_Code=dict['Conversion_Code'],
                               Target_FeatureDescription=dict['Target_FeatureDescription'],
                               Target_Expected_Output=dict['Target_Expected_Output'],
                               Target_ActualCode=dict['Target_ActualCode'],
                               Feature_Approval_Date=dict['Feature_Approval_Date'])
    attachment_data_old = Attachments.objects.filter(Attachment__contains=str(old_migration_type))
    attachment_data_old_values = attachment_data_old.values()
    data = []
    for x in attachment_data_old_values:
        data.append(x['Attachment'])
    data1 = []
    for y in data:
        my_regex = r"\b(?=\w)" + re.escape(old_migration_type) + r"\b(?!\w)"
        if re.search(my_regex, y, re.IGNORECASE):
            data1.append(y)
    for z in data1:
        attachment_data_old = Attachments.objects.filter(Attachment=str(z))
        for dict in attachment_data_old.values():
            object_type = dict['Attachment'].split('/')[3]
            feature_name = dict['Attachment'].split('/')[4]
            Attachments.objects.create(Project_Version_Id=dict['Project_Version_Id'],
                                       Feature_Version_Id=dict['Feature_Version_Id'],
                                       AttachmentType=dict['AttachmentType'], filename=dict['filename'],
                                       Attachment=dict['Attachment'].replace(old_migration_type, new_migration_type),
                                       Feature_Id=Feature.objects.get(Migration_TypeId=new_migration_type,
                                                                      Project_Version_Id=dict['Project_Version_Id'],
                                                                      Feature_Version_Id=dict['Feature_Version_Id'],
                                                                      Object_Type=object_type,
                                                                      Feature_Name=feature_name))

    source_path = 'media/' + old_migration_type + '/'
    sas_token = generate_account_sas(account_name=account_name, account_key=account_key,
                                     resource_types=ResourceTypes(service=True, container=True, object=True),
                                     permission=AccountSasPermissions(read=True),
                                     expiry=datetime.utcnow() + timedelta(hours=1))
    source_blob_service_client = BlobServiceClient(
        account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
    des_blob_service_client = BlobServiceClient(
        account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
    source_container_client = source_blob_service_client.get_container_client(container_name_var)
    blob_list = source_container_client.list_blobs(name_starts_with=source_path)

    if blob_list:
        for blob in blob_list:
            source_blob = source_container_client.get_blob_client(blob)
            source_url = source_blob.url + '?' + sas_token
            source_blob.blob_name = source_blob.blob_name.replace(old_migration_type, new_migration_type)
            des_blob_service_client.get_blob_client(
                container_name_var, source_blob.blob_name).start_copy_from_url(source_url)
    return Response("New Migration type created successfully based on given old migration type")


@api_view(['GET'])
def import_folders_prod(request):
    connect_str = fileshare_connectionString
    container_name = container_name_var
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    local_path = path
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    my_container = blob_service_client.get_container_client(container_name)
    my_blobs_media = my_container.list_blobs(name_starts_with='media')
    if my_blobs_media:
        media_path = path + '/media/'
        if os.path.exists(media_path):
            shutil.rmtree(media_path)
        for blob in my_blobs_media:
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            my_container = blob_service_client.get_container_client(container_name)
            bytes = my_container.get_blob_client(blob).download_blob().readall()
            download_file_path = os.path.join(local_path, blob.name)
            os.makedirs(os.path.dirname(download_file_path), exist_ok=True)
            with open(download_file_path, "wb") as file:
                file.write(bytes)
    my_blobs_modules = my_container.list_blobs(name_starts_with='Modules')
    if my_blobs_modules:
        modules_path = path + '/Modules/'
        if os.path.exists(modules_path):
            shutil.rmtree(modules_path)
        for blob in my_blobs_modules:
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            my_container = blob_service_client.get_container_client(container_name)
            bytes = my_container.get_blob_client(blob).download_blob().readall()
            download_file_path = os.path.join(local_path, blob.name)
            os.makedirs(os.path.dirname(download_file_path), exist_ok=True)
            with open(download_file_path, "wb") as file:
                file.write(bytes)
    return Response("Folders imported successfully to local folder")


@api_view(['POST'])
def user_migration_listperuser(request):
    email = request.data['User_Email']
    user_object = Users.objects.get(email=email)
    user_admin_access = user_object.user_migrations
    final_list = []
    if user_admin_access == '' or user_admin_access == None:
        return Response(final_list)
    else:
        user_admin_access_list = user_admin_access.split(',')
        user_admin_access_list = [x for x in user_admin_access_list if x != '']
        inter_dict = {}
        for mig in user_admin_access_list:
            inter_dict['Migration_TypeId'] = mig
            final_list.append(inter_dict.copy())
        return Response(final_list)


@api_view(['POST'])
def remove_user_admin_permissions(request):
    email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    user_object = Users.objects.get(email=email)
    user_admin_access = user_object.user_migrations
    if mig_type in user_admin_access:
        user_admin_access = user_admin_access.replace(mig_type + ',', '')
        user_object.user_migrations = user_admin_access
        user_object.save()
        appr_data = Approvals.objects.filter(User_Email=email, Migration_TypeId=mig_type)
        appr_data.delete()
        perm_data = Permissions.objects.filter(User_Email=email, Migration_TypeId=mig_type)
        perm_data.delete()
    return Response("Migration Type Removed from User Migrations")


@api_view(['GET', 'POST'])
def get_latest_feature_version_modules(request):
    migration = request.data['Migration_TypeId']
    if migration != 'undefined':
        path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists(path + '/Conversion_Modules/'):
            os.makedirs(path + '/Conversion_Modules/')
        container_client = azure_connection()
        del_blobs = container_client.list_blobs(name_starts_with='Conversion_Modules')
        if del_blobs:
            for blob in del_blobs:
                container_client.delete_blobs(blob)

        object_types_old = migrations.objects.filter(Migration_TypeId=migration).values('Object_Type').distinct()
        object_types_old_list = [dict['Object_Type'] for dict in object_types_old if dict['Object_Type'] != '']
        if object_types_old_list:
            excel_name = path + '/Conversion_Modules/' + migration + '.xlsx'
            workbook = xlsxwriter.Workbook(excel_name)
            for object_i in object_types_old_list:
                feature_names_old = Feature.objects.filter(Migration_TypeId=migration, Object_Type=object_i).values(
                    'Feature_Name').distinct()
                feature_names_old_list = [dict['Feature_Name'] for dict in feature_names_old if
                                          dict['Feature_Name'] != '']

                worksheet = workbook.add_worksheet(object_i)
                f_names_list = []
                keywords_list = []
                level_list = []
                predecessor_list = []
                estimation_list = []
                for feature in feature_names_old_list:
                    feature_versions_old = Feature.objects.filter(Migration_TypeId=migration, Object_Type=object_i,
                                                                  Feature_Name=feature,
                                                                  Feature_version_approval_status='Approved').values(
                        'Project_Version_Id', 'Feature_Version_Id')
                    feature_versions_old_list = []
                    for dict in feature_versions_old:
                        feature_versions_old_list.append(
                            str(dict['Project_Version_Id']) + '.' + str(dict['Feature_Version_Id']))

                    feature_versions_old_list = sorted(feature_versions_old_list, key=float)
                    if feature_versions_old_list:
                        latest_version = max(feature_versions_old_list)
                        prj_ver = latest_version.split('.')[0].strip()
                        feat_ver = latest_version.split('.')[1].strip()
                        latest_feature_data = Feature.objects.filter(Migration_TypeId=migration, Object_Type=object_i,
                                                                     Feature_Name=feature, Project_Version_Id=prj_ver,
                                                                     Feature_Version_Id=feat_ver).values()

                        feature_name = latest_feature_data[0]['Feature_Name']
                        keywords = latest_feature_data[0]['Keywords']
                        level = latest_feature_data[0]['Level']
                        predecessor = latest_feature_data[0]['Sequence']
                        estimation = latest_feature_data[0]['Estimations']

                        f_names_list.append(feature_name)
                        keywords_list.append(keywords)
                        level_list.append(level)
                        predecessor_list.append(predecessor)
                        estimation_list.append(int(estimation))
                        latest_version_feature_id = latest_feature_data[0]['Feature_Id']
                        module_path = 'Modules/' + migration + '/' + 'Project_V' + prj_ver + '/' + object_i + '/' + feature + '/' + 'Feature_V' + feat_ver + '/'
                        conversion_module_path = 'Conversion_Modules/'+ migration + '/' + object_i + '/'
                        sas_token = generate_account_sas(account_name=account_name, account_key=account_key,
                                                         resource_types=ResourceTypes(service=True, container=True,object=True),
                                                         permission=AccountSasPermissions(read=True),
                                                         expiry=datetime.utcnow() + timedelta(hours=1))
                        source_blob_service_client = BlobServiceClient(
                            account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)
                        des_blob_service_client = BlobServiceClient(
                            account_url=f'https://{account_name}.blob.core.windows.net/', credential=account_key)

                        attachments_data = Attachments.objects.filter(Feature_Id=latest_version_feature_id,
                                                                      AttachmentType='Conversion')
                        if attachments_data:
                            attachment_module_path = 'media/' + migration + '/' + 'Project_V' + prj_ver + '/' + object_i + '/' + feature + '/' + 'Feature_V' + feat_ver + '/Conversion/'
                            source_container_client = source_blob_service_client.get_container_client(container_name_var)
                            blob_list = source_container_client.list_blobs(name_starts_with=attachment_module_path)
                            if blob_list:
                                for blob in blob_list:
                                    source_blob = source_container_client.get_blob_client(blob)
                                    source_url = source_blob.url + '?' + sas_token
                                    des_blob_service_client.get_blob_client(
                                        container_name_var, conversion_module_path + feature_name + '.py').start_copy_from_url(source_url)
                        else:
                            source_container_client = source_blob_service_client.get_container_client(container_name_var)
                            blob_list = source_container_client.list_blobs(name_starts_with=module_path)
                            if blob_list:
                                for blob in blob_list:
                                    source_blob = source_container_client.get_blob_client(blob)
                                    source_url = source_blob.url + '?' + sas_token
                                    des_blob_service_client.get_blob_client(
                                        container_name_var, conversion_module_path + feature_name + '.py').start_copy_from_url(source_url)
                            else:
                                print("No module found")
                row_length = len(f_names_list)
                serial_list = [i for i in range(1, row_length + 1)]
                data_dictionary = {'Serial No.': serial_list,
                                   'Feature Name': f_names_list,
                                   'Keywords': keywords_list,
                                   'Level': level_list,
                                   'Predecessor': predecessor_list,
                                   'Estimation': estimation_list}
                col_num = 0
                format = workbook.add_format({'bold': True, 'border': 1})
                format.set_align('center')
                format2 = workbook.add_format({'border': 1})
                for key, value in data_dictionary.items():
                    worksheet.write(0, col_num, key, format)
                    worksheet.write_column(1, col_num, value, format2)
                    col_num += 1
                worksheet.set_column(1, 4, 35)
            workbook.close()
            file_path_on_azure = 'Conversion_Modules/' + migration + '.xlsx'
            file_path_on_local = path + '/Conversion_Modules/' + migration + '.xlsx'
            container_client = azure_connection()
            blob_client = container_client.get_blob_client(file_path_on_azure)
            with open(file_path_on_local, 'rb') as data:
                blob_client.upload_blob(data)
            os.remove(file_path_on_local)
            shutil.rmtree(path + '/Conversion_Modules/')
        else:
            return Response("No Modules Found for given Migration type")
        deploy_object = Deploy.objects.get(Migration_TypeId=migration, Deployment_Status='Deploy in Progress')
        deploy_object.Deploy_End_Time = datetime.now()
        deploy_object.Deployment_Status = 'Completed'
        deploy_object.save()
        return Response("Modules Prepared for given Migration type")
    else:
        return Response("Please Select Migration Type for Deploy")


@api_view(['GET'])
def deploy_table(request):
    deploy_data = Deploy.objects.all()
    serializer = deployserializer(deploy_data, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
def create_deploy_record(request):
    migration = request.data['Migration_TypeId']
    if migration != 'undefined':
        deploy_start_time = datetime.now()
        Deploy.objects.create(Migration_TypeId=migration, Deploy_Start_Time=deploy_start_time)
    return Response("Record created in deploy table")


@api_view(['POST'])
def permission_edit_remove(request):
    action = request.data['Action']
    email = request.data['User_Email']
    mig_type = request.data['Migration_TypeId']
    object_type = request.data['Object_Type']
    feature_name = request.data['Feature_Name']
    access_type = request.data['Access_Type']
    new_expiry_date = request.data['New_Expiry_Date']
    new_access_type = request.data['New_Access_Type']
    if action == 'Edit':
        if new_access_type in ('', None) or new_expiry_date in ('', None):
            return Response("Please input access type or expiry date")
        else:
            appr_data = Approvals.objects.get(User_Email=email, Migration_TypeId=mig_type, Object_Type=object_type,
                                              Feature_Name=feature_name, Access_Type=access_type)
            appr_data.Access_Type = new_access_type
            appr_data.Expiry_date = new_expiry_date
            appr_data.save()
            perm_data = Permissions.objects.get(User_Email=email, Migration_TypeId=mig_type, Object_Type=object_type,
                                                Feature_Name=feature_name, Access_Type=access_type)
            perm_data.Access_Type = new_access_type
            perm_data.Expiry_date = new_expiry_date
            perm_data.save()
            return Response("Permission updated successfully")
    elif action == 'Remove':
        appr_data = Approvals.objects.get(User_Email=email, Migration_TypeId=mig_type, Object_Type=object_type,
                                          Feature_Name=feature_name, Access_Type=access_type)
        appr_data.delete()
        perm_data = Permissions.objects.get(User_Email=email, Migration_TypeId=mig_type, Object_Type=object_type,
                                            Feature_Name=feature_name, Access_Type=access_type)
        perm_data.delete()
        return Response("Permission deleted successfully")
