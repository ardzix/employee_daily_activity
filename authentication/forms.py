from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information"""
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes for styling
        self.fields['email'].widget.attrs.update({
            'class': 'w-full bg-nft-gray border border-nft-light rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nft-primary focus:border-transparent',
            'placeholder': 'Enter your email address'
        })
        
        self.fields['first_name'].widget.attrs.update({
            'class': 'w-full bg-nft-gray border border-nft-light rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nft-primary focus:border-transparent',
            'placeholder': 'Enter your first name'
        })
        
        self.fields['last_name'].widget.attrs.update({
            'class': 'w-full bg-nft-gray border border-nft-light rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nft-primary focus:border-transparent',
            'placeholder': 'Enter your last name'
        })
        
        # Add field labels
        self.fields['email'].label = 'Email Address'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists for another user
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This email address is already in use.")
        return email 