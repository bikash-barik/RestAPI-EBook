from rest_framework import serializers
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed


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

        # today = date.today()
        # permission_data = Permissions.objects.filter(User_Email=user_email).values()
        # for dict in permission_data:
        #     end_date = dict['Expiry_date']
        #     if end_date < today:
        #         record = Permissions.objects.get(User_Email=dict['User_Email'],
        #                                          Migration_TypeId=dict['Migration_TypeId'], Expiry_date=end_date,
        #                                          Feature_Name=dict['Feature_Name'], Access_Type=dict['Access_Type'],
        #                                          Object_Type=dict['Object_Type'])
        #         record.delete()
        #         approval_record = Approvals.objects.get(User_Email=dict['User_Email'],
        #                                                 Migration_TypeId=dict['Migration_TypeId'],
        #                                                 Feature_Name=dict['Feature_Name'],
        #                                                 Access_Type=dict['Access_Type'],
        #                                                 Object_Type=dict['Object_Type'])
        #         approval_record.delete()
        return data

class Resetpasswordemailserializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    class Meta:
        fields = ['email']


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


class resendemailserializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('email',)


class migrationcreateserializer(serializers.ModelSerializer):
    class Meta:
        model = Migrations
        fields = '__all__'

class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Features
        fields = "__all__"