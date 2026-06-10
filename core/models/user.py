from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email é obrigatório')

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)

        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('buyer', 'Comprador'),
        ('seller', 'Vendedor'),
    ]

    email = models.EmailField(unique=True)

    name = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
    auto_now_add=True,
    null=True,
    blank=True
)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='buyer'
    )

    birth_date = models.DateField(
        null=True,
        blank=True
    )

    profile_image = models.ImageField(
        upload_to='users/',
        null=True,
        blank=True
    )

    bio = models.TextField(
        null=True,
        blank=True
    )

    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
