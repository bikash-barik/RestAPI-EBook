import mimetypes,json,re,sys,jwt,xlsxwriter,shutil
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from .serializers import *
from rest_framework import status,generics
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from django.core import mail
from CookBook_Backend.settings import EMAIL_HOST_USER
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from Config.config import frontend_url, fileshare_connectionString, container_name_var,account_name,account_key

class MyObtainTokenPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer

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


class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'success': True, 'msg': 'Password Reset Success'}, status=status.HTTP_200_OK)


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

@api_view(['POST'])
def migrationcreate(request):
    project_id = request.data['Project_Version_Id']
    migration_name = request.data['Migration_Name']
    project_version_limit = request.data['Project_Version_limit']
    feature_version_limit = request.data['Feature_Version_Limit']

    serializer = migrationcreateserializer(data=request.data)
    check_migration = Migrations.objects.filter(Project_Version_Id=project_id, Migration_Name=migration_name)

    if not check_migration:
        if project_version_limit == '' and feature_version_limit == '':
            if serializer.is_valid():
                serializer.save(Project_Version_Limit = 3, Feature_Version_Limit = 3)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            if serializer.is_valid():
                serializer.save(Project_Version_Limit=project_version_limit,Feature_Version_Limit=feature_version_limit)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response('Migration Type already exist')

@api_view(['POST'])
def object_type_create(request):
    project_id = request.data['Project_Version_Id']
    migration_name = request.data['Migration_Name']
    object_type_str = request.data['Object_Type_Str']

    object_type_str_list = object_type_str.split('/')

    if len(object_type_str_list) == 1:
        object_type = object_type_str_list[0]
        check_object = ObjectTypes.objects.filter(Project_Version_Id = project_id,Migration_Name = migration_name,
                                                  Object_Type = object_type)
        if check_object:
            return Response('Object Type already exist')
        else:
            ObjectTypes.objects.create(Project_Version_Id = project_id,Migration_Name = migration_name,
                                       Object_Type = object_type)
            return Response('Object Type created', status=status.HTTP_201_CREATED)
    elif len(object_type_str_list) > 1:
        object_type = object_type_str_list[-1]
        parent_object_type = object_type_str_list[-2]
        p_object = ObjectTypes.objects.get(Project_Version_Id = project_id,Migration_Name = migration_name,
                                            Object_Type = parent_object_type)
        check_object = ObjectTypes.objects.filter(Project_Version_Id = project_id,Migration_Name = migration_name, Object_Type = object_type, Parent_Object_Id = p_object.Object_Id)
        if check_object:
            return Response('Object Type already exist')
        else:
            ObjectTypes.objects.create(Project_Version_Id=project_id, Migration_Name=migration_name,
                                       Object_Type=object_type, Parent_Object_Id = p_object.Object_Id)
            return Response('Object Type created', status=status.HTTP_201_CREATED)


@api_view(['POST'])
def featurecreate(request):
    migration_name = request.data['Migration_Name']
    object_id = request.data['Object_Id']
    feature_name = request.data['Feature_Name']
    project_version = request.data['Project_Version_Id']

    check_feature = Features.objects.filter(Migration_Name = migration_name,Project_Version_Id = project_version,
                                            Object_Id = object_id,Feature_Name = feature_name)
    if check_feature:
        return Response("Feature already present with this version.Kindly request access for it")
    else:
        serializer = FeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(Feature_Version_Id=int(request.data['Feature_Version_Id']) + 1)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['POST'])
# def approval_request_create(request):
#     user_email =request.data['User_Email']
#
#     return Response("Response")


def recursive_menu_creation(project_version,mig_name,parent_object_id):
    inter_dict = {}
    inter_list = []

    sub_objects_data = ObjectTypes.objects.filter(Project_Version_Id=project_version, Migration_Name=mig_name,
                                                  Parent_Object_Id=parent_object_id)
    if sub_objects_data:
        sub_objects_list = [obj['Object_Type'] for obj in sub_objects_data.values()]
        for sub_object in sub_objects_list:
            inter_dict['Object_Type'] = sub_object
            sub_object_id_data = ObjectTypes.objects.filter(Project_Version_Id=project_version, Migration_Name=mig_name,
                                                            Object_Type=sub_object, Parent_Object_Id=parent_object_id)
            sub_object_id = sub_object_id_data.values()[0]['Object_Id']

            sub_features_data = Features.objects.filter(Project_Version_Id=project_version, Migration_Name=mig_name,
                                                        Object_Id=sub_object_id)
            feature_names = [obj['Feature_Name'] for obj in sub_features_data.values()]
            feature_dict = {}
            feature_names_list = []
            for feature in feature_names:
                feature_dict['Feature_Name'] = feature
                feature_names_list.append(feature_dict.copy())
            inter_dict['Sub_Menu'] = feature_names_list

            sub_inter_dict = recursive_menu_creation(project_version, mig_name, sub_object_id)

            inter_dict['Sub_Objects'] = sub_inter_dict
            inter_list.append(inter_dict.copy())
    else:
        inter_list = []
    return inter_list


@api_view(['POST'])
def menu_view_creation(request):
    email = request.data['User_Email']
    mig_name = request.data['Migration_Name']
    project_version = request.data['Project_Version_Id']

    parent_objects_data = ObjectTypes.objects.filter(Project_Version_Id = project_version, Migration_Name = mig_name,
                                                     Parent_Object_Id = '')
    parent_objects_list = [ obj['Object_Type'] for obj in parent_objects_data.values()]

    final_dict = {}
    final_list = []

    for object_type in parent_objects_list:

        object_id_data = ObjectTypes.objects.filter(Project_Version_Id = project_version, Migration_Name = mig_name,
                                                    Object_Type = object_type,Parent_Object_Id = '')
        object_id = object_id_data.values()[0]['Object_Id']

        final_dict['Object_Type'] = object_type

        features_data = Features.objects.filter(Project_Version_Id = project_version, Migration_Name = mig_name,
                                                Object_Id = object_id)
        feature_names = [obj['Feature_Name'] for obj in features_data.values()]
        feature_dict = {}
        feature_names_list = []
        for feature in feature_names:
            feature_dict['Feature_Name'] = feature
            feature_names_list.append(feature_dict.copy())
        final_dict['Sub_Menu'] = feature_names_list

        inter_list = recursive_menu_creation(project_version, mig_name, object_id)

        final_dict['Sub_Objects'] = inter_list
        final_list.append(final_dict.copy())
    return Response(final_list)














