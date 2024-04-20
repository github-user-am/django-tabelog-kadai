from django.db import models
from django.apps import apps
from django.contrib import auth
from django.core.mail import send_mail
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.validators import UnicodeUsernameValidator
import datetime as dt
from django.db.models import Avg, Count

# Create your models here.

# General
DAY_OF_THE_WEEK = (
    ('sunday', '日'),
    ('monday', '月'),
    ('tuesday', '火'),
    ('wednesday', '水'),
    ('thursday', '木'),
    ('friday', '金'),
    ('saturday', '土'),
    ('none_holiday', '定休日なし'),
)

# For Administrators
class MyUserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, email, nickname, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        
        user = self.model(email=email, nickname=nickname, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, nickname, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', False)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, nickname, password, **extra_fields)
    
    def create_superuser(self, email, nickname, password, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
  
        return self._create_user(email, nickname, password, **extra_fields)

# User Model
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _("email address"),
        unique = True
    )
    nickname = models.CharField(
        _("nickname"),
        max_length = 150,
        unique = True,
        help_text = "150文字以内で文字や数字を使うことができます（記号は「@/./+/-/_」のみ使用可能）。" ,
        blank = True,
        null = True,
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default = False,
        help_text = _("Designates whether the user can log into this admin site."),
    )
    is_admin = models.BooleanField(
        _("admin status"),
        default = False,
        help_text = _("Designates whether the user can manage restaurant"),
    )
    is_active = models.BooleanField(
        _('active'),
        default = True,
        help_text = _(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length = 20,
        blank = True,
    )
    date_joined = models.DateTimeField(
        _("date joined"),
        default = timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now = True,
    )

    # AbstractBaseUserにはMyUserManagerが必要
    objects = MyUserManager()

    # 一意の識別子
    EMAIL_FIELD = "email"
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    # ユーザー名を返す関数
    def get_nickname(self):
        return self.nickname


class Category(models.Model):
    """
    カテゴリモデル
    """
    category_name = models.CharField(
        _("category name"),
        max_length=150,
    )
    create_at = models.DateTimeField(
        _("create at"),
        default=timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.category_name


class Restaurant(models.Model):
    """
    店舗モデル
    """
    restaurant_category = models.ManyToManyField(
        Category,
        related_name = 'restaurant_categories',
        blank = True,
    )
    # 店舗の管理者
    restaurant_admin = models.ForeignKey(
        CustomUser,
        on_delete = models.CASCADE,
    )
    restaurant_name = models.CharField(
        _("restaurant name"),
        max_length = 150,
    )
    restaurant_image = models.ImageField(
        _("restaurant image"),
        blank = True,
        default = 'noImage.png',
    )
    description = models.TextField(
        _("description"),
        blank = True,
        null = True,
    )
    postal_code = models.CharField(
        _("postal code"),
        max_length = 30,
    )
    address = models.CharField(
        _("address"),
        max_length = 200,
    )
    opening = models.TimeField(
        _("opening"),
        default = dt.time(00, 00),
    )
    closing = models.TimeField(
        _("closing"),
        default = dt.time(00, 00),
    )
    regular_holiday = models.CharField(
        _("regular holiday"),
        max_length = 20,
        choices = DAY_OF_THE_WEEK,
    )
    seat_number = models.PositiveSmallIntegerField(
        _("seat number"),
        default = 1,
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length = 20,
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now = True,
    )

    class Meta:
        verbose_name = _("restaurant")
        verbose_name_plural = _("restaurants")

    def __str__(self):
        return self.restaurant_name
    
    # 定休日を日本語で取得
    def get_regular_holiday(self):
        regular_holiday = self.regular_holiday
        if regular_holiday == 'sunday':
            regular_holiday = '日'
        elif regular_holiday == 'monday':
            regular_holiday = '月'
        elif regular_holiday == 'tuesday':
            regular_holiday = '火'
        elif regular_holiday == 'wednesday':
            regular_holiday = '水'
        elif regular_holiday == 'thursday':
            regular_holiday = '木'
        elif regular_holiday == 'friday':
            regular_holiday = '金'
        elif regular_holiday == 'saturday':
            regular_holiday = '土'
        else:
            regular_holiday = 'なし'
        return regular_holiday
    
    # カテゴリ名を取得
    def get_category_name(self):
        restaurant_id = self.id
        categories = Category.objects.filter(restaurant_categories=restaurant_id)
        return categories
    
    # レビュー数を取得
    def review_count(self):
        review_count = Review.objects.filter(restaurant_id=self.id).aggregate(Count('restaurant_id'))
        if review_count['restaurant_id__count']:
            return review_count['restaurant_id__count']
        else:
            return 0

    # レビュー平均値を返す
    def avg_score(self):
        reviews = Review.objects.filter(restaurant_id=self.id).aggregate(Avg('score'))

        if reviews['score__avg']:
            return reviews['score__avg']
        else:
            return 0
        
    def avg_star_icon(self):
        reviews = Review.objects.filter(restaurant_id=self.id).aggregate(Avg('score'))
        avg = reviews['score__avg']

        if avg:
            if avg >= 4.5:
                return("★★★★★")
            elif 4.5 > avg >= 3.5:
                return("★★★★☆")
            elif 3.5 > avg >= 2.5:
                return("★★★☆☆")
            elif 2.5 > avg >= 1.5:
                return("★★☆☆☆")
            elif 1.5 > avg >= 0.5:
                return("★☆☆☆☆")
            else:
                return("☆☆☆☆☆")
        else:
            return("☆☆☆☆☆")


class Favorite(models.Model):
    """
    お気に入りモデル
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete = models.CASCADE,
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete = models.CASCADE
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now,
    )


class Review(models.Model):
    """
    レビューモデル
    """
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete = models.CASCADE
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete = models.CASCADE,
    )
    score = models.FloatField(
        _("score"),
        choices = (
            (1.0, '1'),
            (2.0, '2'),
            (3.0, '3'),
            (4.0, '4'),
            (5.0, '5'),
        )
    )
    review_title = models.CharField(
        _("review title"),
        max_length = 100,
    )
    review_comment = models.TextField(
        _("review comment"),
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now = True,
    )

    # レビューした人のユーザー名を取得
    def get_reviewer(self):
        reviewer = CustomUser.objects.get(id=self.user_id)
        nickname = reviewer.nickname
        return nickname

    # 評価の☆の数を取得
    def get_star_score(self):
        score = self.score
        if score == 5.0:
            return("★★★★★")
        elif score == 4.0:
            return("★★★★☆")
        elif score == 3.0:
            return("★★★☆☆")
        elif score == 2.0:
            return("★★☆☆☆")
        elif score == 1.0:
            return("★☆☆☆☆")
        else:
            return("☆☆☆☆☆")

    # レビューに対するGood数
    def good_count(self):
        good_count = Good.objects.filter(review_id=self.id).aggregate(Count('review_id'))
        if good_count['review_id__count']:
            return good_count['review_id__count']
        else:
            return 0


class Good(models.Model):
    """
    レビューに対するGoodモデル
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now
    )


class Reservation(models.Model):
    """
    予約モデル
    """
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete = models.CASCADE
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete = models.CASCADE,
    )
    reservation_date = models.DateField(
        _("reservation date"),
    )
    reservation_start = models.DateTimeField(
        _("reservation start"),
    )
    reservation_end = models.DateTimeField(
        _("reservation end"),
    )
    number_of_people = models.PositiveSmallIntegerField(
        _("number of people"),
        choices = (
            (0, '0'),
            (1, '1'),
            (2, '2'),
            (3, '3'),
            (4, '4'),
            (5, '5'),
            (6, '6'),
            (7, '7'),
            (8, '8'),
            (9, '9'),
            (10, '10'),
            (11, '11'),
            (12, '12'),
            (13, '13'),
            (14, '14'),
            (15, '15'),
            (16, '16'),
            (17, '17'),
            (18, '18'),
            (19, '19'),
            (20, '20'),
        )
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now = True,
    )


class AccessHistory(models.Model):
    """
    店舗閲覧履歴のモデル
    """
    url = models.URLField()
    user = models.ForeignKey(
        CustomUser,
        on_delete = models.CASCADE,
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete = models.CASCADE,
        blank = True,
        null = True,
    )
    time = models.DateTimeField(
        auto_now =True
    )

    class Meta:
        verbose_name = _("accesshistory")
        verbose_name_plural = _("accesshistories")


class Subscriber(models.Model):
    """
    有料会員のモデル
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete = models.CASCADE,
    )
    create_at = models.DateTimeField(
        _("create at"),
        default = timezone.now
    )
    update_at = models.DateTimeField(
        _("last update"),
        auto_now = True,
    )
    stripe_id = models.CharField(
        max_length = 255,
        null = True,
        blank = True,
    )
    subscription_id = models.CharField(
        max_length = 255,
        null = True,
        blank = True,
    )


class SubscriptionProduct(models.Model):
    """
    サブスクリプション商品
    """
    name = models.CharField(
        max_length=100,
    )
    stripe_product_id = models.CharField(
        max_length=100,
    )

    # admin画面で商品名表示
    def __str__(self):
        return self.name


class SubscriptionPrice(models.Model):
    """
    サブスクリプション価格
    """
    subscription_product = models.ForeignKey(
        SubscriptionProduct,
        on_delete=models.CASCADE
    )
    stripe_price_id = models.CharField(
        max_length=100,
    )
    price = models.IntegerField(
        default=0,
    )

# トランザクションマスタ
class Transaction(models.Model):
    # 購入日
    date   = models.DateTimeField(
        _("date"),
        default = timezone.now
    )
    # 購入者
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )
    # 購入商品
    product = models.ForeignKey(
        SubscriptionProduct,
        on_delete=models.CASCADE
    )
    # 支払い金額
    product_amount = models.IntegerField(
        default=0
    )

    # admin画面で商品名表示
    def __str__(self):
        return self.date + '_' + self.product  + '_' + self.customer