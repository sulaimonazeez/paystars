from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
  user = models.OneToOneField(User, on_delete=models.CASCADE)
  phone_number = models.CharField(max_length=15, unique=True,null=True, blank=True)
  nin = models.CharField(max_length=12,unique=True, null=True,blank=True)

class Balance(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
  def __str__(self):
    return f"{self.user.username} - {self.balance}"

class VirtualsAccountings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=50)
    order_ref = models.CharField(max_length=100)
    def __str__(self):
        return f"{self.user.username} - {self.account_number}"


class UserProfiles(models.Model):
  user = models.OneToOneField(User, on_delete=models.CASCADE)
  night_mode = models.BooleanField(default=False)
  


class WalletFunding(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  fund_amount = models.DecimalField(max_digits=10, decimal_places=2)
  settle_amount = models.DecimalField(max_digits=10, decimal_places=2)
  header = models.CharField(max_length=255)
  transaction_reference = models.CharField(max_length=255, unique=True)
  fees = models.DecimalField(max_digits=10, decimal_places=2)
  desciption = models.TextField()
  status = models.BooleanField(default=False)
  date = models.DateField(auto_now_add=True)
  
  def __str__(self):
    return f"{self.user.username} - {self.new_balance}"
  
"""class Development(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  balance = models.ForeignKey(Balance, on_delete=models.CASCADE)
  charge = models.DecimalField(max_digits=10, decimal_places=2)
  service = models.CharField(max_length=255)
  
  amount = models.DecimalField(max_digits=10, decimal_places=2)
  phone = models.CharField(max_length=255)
  data_amount = models.CharField(max_length=255)
  transaction_id = models.CharField(max_length=2000)
  date = models.DateField(auto_now_add=True)
  status = models.BooleanField(default=False)
  def __str__(self):
    return self.user.username"""
  

class Download(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  downloaded = models.IntegerField()
  
  def __str__(self):
    return self.user.username
    
class GeneratePin(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  pin = models.CharField(max_length=255, default="1111")
  
  def __str__(self):
    return self.user.username
    
class AccountUpgrade(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  upgrade = models.BooleanField(default=False)
  
  def __str__(self):
    return self.user.username

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    NETWORK_CHOICES = [
        ('airtel', 'Airtel'),
        ('mtn', 'MTN'),
        ('glo', 'Glo'),
        ('9mobile', '9Mobile'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.CharField(max_length=255)
    reference = models.CharField(max_length=50, unique=True)
    network = models.CharField(max_length=10, choices=NETWORK_CHOICES)
    data_plan = models.CharField(max_length=50)
    data_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status_code = models.BooleanField(default=False)
    balance = models.ForeignKey(Balance, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    def __str__(self):
        return f"{self.network} - {self.data_plan} ({self.status})"