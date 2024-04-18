from django import forms
from . import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Category, Restaurant, Favorite, Review, Good, Reservation, AccessHistory, Subscriber, SubscriptionProduct, SubscriptionPrice

# Register your models here.
class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields':('email', 'password')}),
        (_('Personal info'), {'fields':('nickname', 'phone_number')}),
        (_('Permissions'), {'fields':('is_admin', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    form = forms.MyUserChangeForm
    add_form = forms.MyUserCreationForm
    list_display = ('email', 'nickname', 'is_superuser', 'is_admin')
    list_filter = ('is_superuser', 'is_admin',)
    search_fields = ('email', 'nickname')
    ordering = ('id',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'category_name',)
    ordering = ('id',)

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant_name', 'create_at',)
    ordering = ('id',)

class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'restaurant',)
    ordering = ('id',)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'user',)
    ordering = ('id',)

class GoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user',)
    ordering = ('id',)

class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'user',)
    ordering = ('id',)

class AccessHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'user',)
    ordering = ('id',)

class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user',)
    ordering = ('id',)

class SubscriptionProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'stripe_product_id',)
    ordering = ('id',)

class SubscriptionPriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription_product', 'stripe_price_id', 'price',)
    ordering = ('id',)

admin.site.register(CustomUser, MyUserAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Good, GoodAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(AccessHistory, AccessHistoryAdmin)
admin.site.register(Subscriber, SubscribeAdmin)
admin.site.register(SubscriptionProduct, SubscriptionProductAdmin)
admin.site.register(SubscriptionPrice, SubscriptionPriceAdmin)