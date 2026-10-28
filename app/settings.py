import os
from datetime import timedelta
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()
MODE = os.getenv('MODE', 'DEVELOPMENT')
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure')
DEBUG = os.getenv('DEBUG', 'True') == 'True' if MODE == 'DEVELOPMENT' else os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'http://localhost:8000']
CORS_ALLOW_ALL_ORIGINS = True
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions',
    'django.contrib.messages','django.contrib.staticfiles','cloudinary_storage','cloudinary','corsheaders',
    'django_extensions','django_filters','drf_spectacular','rest_framework','pagamentos','uploader','core','posts',
]
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware','corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'app.urls'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'app.wsgi.application'
DATABASES = {'default': dj_database_url.config(default='sqlite:///db.sqlite3', conn_max_age=600, conn_health_checks=True)}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
FILE_UPLOAD_PERMISSIONS = 0o640
if MODE == 'DEVELOPMENT':
    MY_IP = os.getenv('MY_IP', '127.0.0.1')
else:
    CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STORAGES = {'default':{'BACKEND':'cloudinary_storage.storage.MediaCloudinaryStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.User'
SPECTACULAR_SETTINGS = {'TITLE':'Reveste API','DESCRIPTION':'API da plataforma Reveste.','VERSION':'1.0.0'}
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PAGINATION_CLASS':'app.pagination.CustomPagination',
    'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema','PAGE_SIZE':10,
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME':timedelta(minutes=180),'REFRESH_TOKEN_LIFETIME':timedelta(days=1),'AUTH_HEADER_TYPES':('Bearer',)}
MERCADO_PAGO_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_ACCESS_TOKEN', '')
MERCADO_PAGO_WEBHOOK_SECRET = os.getenv('MERCADO_PAGO_WEBHOOK_SECRET', '')
MERCADO_PAGO_WEBHOOK_URL = os.getenv('MERCADO_PAGO_WEBHOOK_URL', '')
