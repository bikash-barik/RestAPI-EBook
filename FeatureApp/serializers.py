from rest_framework import serializers
from .models import *
from datetime import date
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, max_length=68, write_only=True)
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)

    class Meta:
        model = Users
        fields = ['password', 'token', 'uidb64']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')

            id = force_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('The reset link is invalid', 401)

            user.set_password(password)
            user.save()
        except Exception as e:
            raise AuthenticationFailed('The reset link is invalid', 401)
        return super().validate(attrs)


class Resetpasswordemailserializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    class Meta:
        fields = ['email']


class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approvals
        fields = "__all__"


class migrationcreateserializer(serializers.ModelSerializer):
    class Meta:
        model = migrations
        fields = '__all__'


class migrationviewserializer(serializers.ModelSerializer):
    title = serializers.CharField(source='Migration_TypeId')
    code = serializers.CharField(source='Code')

    class Meta:
        model = migrations
        fields = ('title', 'code',)


class objectviewserializer(serializers.ModelSerializer):
    class Meta:
        model = migrations
        fields = ('Object_Type',)


class FeaturedropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('Feature_Name',)


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = "__all__"


class AttachementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachments
        fields = "__all__"


class SequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('Feature_Name',)


class migrationlevelfeatures(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('Feature_Id', 'Feature_Name',)


class ConversionfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachments
        fields = ('Attachment',)


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=Users.objects.all())]
    )

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Users
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        return attrs

    def create(self, request):
        user = Users.objects.create(
            username=self.validated_data['username'],
            email=self.validated_data['email'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name']
        )
        user.set_password(self.validated_data['password'])
        user.is_active = False
        user.save()
        return user


class viewlevelfeatures(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('can_view',)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['username'] = self.user.username
        data['superadmin'] = self.user.is_superuser
        data['useradmin'] = self.user.is_user_admin
        data['email'] = self.user.email
        user_email = data['email']

        today = date.today()
        permission_data = Permissions.objects.filter(User_Email=user_email).values()
        for dict in permission_data:
            end_date = dict['Expiry_date']
            if end_date < today:
                record = Permissions.objects.get(User_Email=dict['User_Email'],
                                                 Migration_TypeId=dict['Migration_TypeId'], Expiry_date=end_date,
                                                 Feature_Name=dict['Feature_Name'], Access_Type=dict['Access_Type'],
                                                 Object_Type=dict['Object_Type'])
                record.delete()
                approval_record = Approvals.objects.get(User_Email=dict['User_Email'],
                                                        Migration_TypeId=dict['Migration_TypeId'],
                                                        Feature_Name=dict['Feature_Name'],
                                                        Access_Type=dict['Access_Type'],
                                                        Object_Type=dict['Object_Type'])
                approval_record.delete()
        return data


class resendemailserializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email',)


class usersserializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email',)


class userssremovepermissionserializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email', 'admin_migrations')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissions
        fields = "__all__"


class migrationformatserializer(serializers.ModelSerializer):
    class Meta:
        model = migrations
        fields = '__all__'


class useradminlistserializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email', 'username',)


class migrationuseradminserializer(serializers.ModelSerializer):
    class Meta:
        model = migrations
        fields = ('Migration_TypeId',)


class deployserializer(serializers.ModelSerializer):
    class Meta:
        model = Deploy
        fields = '__all__'
