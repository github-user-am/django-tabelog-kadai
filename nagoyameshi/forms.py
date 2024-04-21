from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Review, Category, Restaurant
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import default_storage

### For Admin ###
class MyUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('__all__')

class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'nickname')

### Signup Form ###
class SignupForm(forms.Form):
    def check_email(email):
        if CustomUser.objects.filter(email=email):
            raise ValidationError('*既にメールアドレスが登録されています')
    
    def check_nickname(nickname):
        if CustomUser.objects.filter(nickname=nickname):
            raise ValidationError('*ニックネームは既に使われています')
    
    email = forms.EmailField(label='メールアドレス', validators=[check_email])
    nickname = forms.CharField(label='ユーザー名', max_length=150, validators=[check_nickname])
    password = forms.CharField(label='パスワード', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='パスワード再入力', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        return cleaned_data
    
    # パスワードが一致するか
    def clean_confirm_password(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password != confirm_password:
            raise ValidationError('*パスワードが一致しません')
        return password

### Login Form ###
class LoginForm(forms.Form):
    email = forms.EmailField(label='メールアドレス')
    password = forms.CharField(label='パスワード', widget=forms.PasswordInput)

### Update Form ###
class UpdateForm(forms.ModelForm):
    email = forms.EmailField(label='メールアドレス')
    nickname = forms.CharField(label='ニックネーム', max_length=150)
    phone_number = forms.CharField(label='電話番号', max_length=20)

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'nickname',
            'phone_number',
        )

### Password Change Form ###
class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(label='現在のパスワード', required=True, max_length=150, widget=forms.PasswordInput)
    new_password = forms.CharField(label='新しいパスワード', required=True, max_length=150, widget=forms.PasswordInput)
    confirm_new_password = forms.CharField(label='パスワード再入力', required=True, max_length=150, widget=forms.PasswordInput)

    def __init__(self, _email, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._email = _email
    
    def clean(self):
        cleaned_data = super(PasswordChangeForm, self).clean()
        return cleaned_data

    # 現在のパスワードは正しいか？
    def clean_current_password(self):
        current_password = self.cleaned_data['current_password']
        if self._email and current_password:
            auth_result = authenticate(email=self._email, password=current_password)
            if not auth_result:
                raise forms.ValidationError(_('現在のパスワードが間違っています。'), code='invalid password')
        return current_password

    # new_passwordとconfirm_passwordが一致するか？
    def clean_confirm_new_password(self):
        new_password = self.cleaned_data['new_password']
        confirm_new_password = self.cleaned_data['confirm_new_password']
        if new_password != confirm_new_password:
            raise forms.ValidationError(_('パスワードが一致しません。'), code='invalid password')
        return new_password

### Review Form ###
class ReviewForm(forms.Form):
    review_title = forms.CharField(max_length=100, label='タイトル')
    review_comment = forms.CharField(widget=forms.Textarea, label='コメント')
    score = forms.ChoiceField(choices=(
            (1.0, '1'),
            (2.0, '2'),
            (3.0, '3'),
            (4.0, '4'),
            (5.0, '5'),
        ), label='評価')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super(ReviewForm, self).clean()
        return cleaned_data

### Reservation Form ###
class ReservationForm(forms.Form):
    number_of_people = forms.ChoiceField(choices=(
            (0, '--'),
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
        ), label='予約人数')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super(ReservationForm, self).clean()
        return cleaned_data

### Create Restaurant Form ###
class CreateRestaurantForm(forms.Form):
    restaurant_category = forms.ModelMultipleChoiceField(
        label = 'カテゴリ',
        queryset=Category.objects.all(),
    )
    restaurant_name = forms.CharField(
        label = '店舗名',
        max_length = 150,
    )
    restaurant_image = forms.ImageField(
        label = '店舗写真',
    )
    description = forms.CharField(
        label = '店舗説明',
        widget = forms.Textarea,
    )
    postal_code = forms.CharField(
        label = '郵便番号',
        max_length = 30,
    )
    address = forms.CharField(
        label = '住所',
        max_length = 200,
    )
    opening = forms.TimeField(
        label = '開店',
    )
    closing = forms.TimeField(
        label= '閉店',
    )
    regular_holiday = forms.ChoiceField(
        label = '定休日',
        choices = (
                ('sunday', '日'),
                ('monday', '月'),
                ('tuesday', '火'),
                ('wednesday', '水'),
                ('thursday', '木'),
                ('friday', '金'),
                ('saturday', '土'),
                ('none_holiday', '定休日なし')
                ),
    )
    seat_number = forms.IntegerField(
        label = '座席数',
    )
    phone_number = forms.CharField(
        label = '電話番号',
        max_length = 20,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super(CreateRestaurantForm, self).clean()
        return cleaned_data

### Update Restaurant Form ###
class UpdateRestaurantForm(forms.ModelForm):
    restaurant_category = forms.ModelMultipleChoiceField(
        label = 'カテゴリ',
        queryset=Category.objects.all(),
    )
    restaurant_name = forms.CharField(
        label = '店舗名',
        max_length = 150,
    )
    restaurant_image = forms.ImageField(
        label = '店舗写真',
    )
    description = forms.CharField(
        label = '店舗説明',
        widget = forms.Textarea,
    )
    postal_code = forms.CharField(
        label = '郵便番号',
        max_length = 30,
    )
    address = forms.CharField(
        label = '住所',
        max_length = 200,
    )
    opening = forms.TimeField(
        label = '開店',
    )
    closing = forms.TimeField(
        label= '閉店',
    )
    regular_holiday = forms.ChoiceField(
        label = '定休日',
        choices = (
                ('sunday', '日'),
                ('monday', '月'),
                ('tuesday', '火'),
                ('wednesday', '水'),
                ('thursday', '木'),
                ('friday', '金'),
                ('saturday', '土'),
                ('none_holiday', '定休日なし')
                ),
    )
    seat_number = forms.IntegerField(
        label = '座席数',
    )
    phone_number = forms.CharField(
        label = '電話番号',
        max_length = 20,
    )

    class Meta:
        model = Restaurant
        fields = (
            'restaurant_category',
            'restaurant_name',
            'restaurant_image',
            'description',
            'postal_code',
            'address',
            'opening',
            'closing',
            'regular_holiday',
            'seat_number',
            'phone_number',
        )

### Update Category Form ###
class UpdateCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('category_name',)