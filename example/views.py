from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import json
from django.db import IntegrityError
from django.contrib import messages
from .models import VirtualsAccountings, UserProfiles, Profile, Balance, Download, AccountUpgrade, GeneratePin, WalletFunding, Transaction
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
#from .services import PaystackService
import logging
from django.http import HttpResponse,HttpResponseRedirect
import random
from django.db import transaction
from django_weasyprint import WeasyTemplateView
from django.views import View
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.db.models import Q
from django.http import JsonResponse
from .services import PayVesselService
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
import uuid
from .purchaser import ProcessPayment


def welcome(request):
  return render(request, "home.html")


@login_required
def notification(request):
  is_night = None
  try:
    nightmode = UserProfiles.objects.get(user=request.user)
    is_night = nightmode.night_mode
  except Exception:
    is_night = False
  return render(request, "notification.html", {"nightmode":is_night})






@login_required
def transaction_history(request):
  try:
    nightmode = UserProfiles.objects.get(user=request.user)
    is_night = nightmode.night_mode
  except UserProfiles.DoesNotExist:
    is_night = False
  dev = Transaction.objects.filter(user=request.user).order_by('-id')[:20]
  return render(request, 'transaction.html', {"nightmode":is_night, "dev": dev})




def register(request):
    # Check if user is already authenticated
    if request.user.is_authenticated:
        return redirect(reverse('home'))

    if request.method == "POST":
        username = request.POST.get("username")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Validate form data
        if password1 and password1 == password2 and username and email:
            try:
                # Create user and save to database
                user = User.objects.create_user(username=username, email=email, password=password1)
                user.first_name = first_name
                user.last_name = last_name
                user.save()

                # Authenticate user
                auto_log = authenticate(username=username, password=password1)
                if auto_log is not None:
                    login(request, auto_log)
                    Profile.objects.create(user=auto_log, phone_number=phone_number)
                    messages.success(request, "Account successfully created")
                    return redirect(reverse('home'))
                else:
                    context = {'error': 'Login failed. Please try again.'}
                    return render(request, 'create.html', context)

            except IntegrityError:
                context = {'error': 'Username or email already exists.'}
                return render(request, 'create.html', context)
            except Exception as e:
                context = {'error': f'An error occurred: {e}'}
                return render(request, 'create.html', context)
        else:
            context = {'error': 'Invalid form submission. Please check your details and try again.'}
            return render(request, 'create.html', context)

    return render(request, 'create.html')






def logged(request):
  #check if user is already authenticated
  if request.user.is_authenticated:
    return redirect("/home")
  
  #check method
  if request.method == "POST":
    try:
      username = request.POST.get("username")
      password = request.POST.get("password")
      auth = authenticate(username=username, password=password)
      if auth is not None:
        login(request, auth)
        messages.success(request, "Successful Login")
        return redirect("/home")
      else:
        messages.error(request, "incorrect Password or Username")
        return render(request, "login.html", {"error": "Invalid Crediential"})
    except Exception as e:
      print(e)
      print("Error occured while login")
      return HttpResponse("Error occured while login")
  return render(request, 'login.html')
  
  
logger = logging.getLogger(__name__)
@login_required
def home(request):
  sufficient, pin, funds, is_generated = False, False, False, False
  message,success, account_no, bank = "","","",""
  #generating account number
  try:
        account_number = PayVesselService.generate_virtual_account(request.user)
        logger.debug(f"Account number response: {account_number}")

        details = account_number['banks'][0]
        logger.debug(f"Details extracted: {details}")

        if not VirtualsAccountings.objects.filter(user=request.user).exists():
            VirtualsAccountings.objects.create(
                user=request.user,
                account_number=details["accountNumber"],
                bank_name=details["bankName"],  # Ensure this is correct
                order_ref=details["trackingReference"]
            )
        result = VirtualsAccountings.objects.get(user=request.user)
        account_no = result.account_number
        bank = result.bank_name
        is_generated = True
  except KeyError as ke:
        logger.error(f"KeyError: {ke}")
        logger.error(f"Account number response structure: {account_number}")
        print(ke)
        is_generated = False
  except Exception as e:
        logger.error(f"Exception occurred: {e}")
        is_generated = False
    
  try:
    uprades = request.GET.get("upgrade")
    if uprades == "true":
      funds = True
      message = "Successful Upgrade to Vendor"
      success = "Successful"
  except Exception:
    print("Not Allowed")
    
  try:
    suff = request.GET.get("sufficient")
    if suff == "false":
      sufficient = True
      message = "Insufficient Fund please add fund"
      success = "ERROR!!"
      
  except Exception:
    print("Not Allowed")
    
  try:
    pi = request.GET.get("pwd")
    if pi == "false":
      pin = True
      message = "Incorrect Password please try again"
      success = "ERROR!!"
  except Exception:
    print("Not Allowed")
  try:
    blc, mycreate = Balance.objects.get_or_create(user=request.user)
    balance = blc
  except Balance.DoesNotExist as e:
    print(e)
  try:
    nightmode, mynight = UserProfiles.objects.get_or_create(user=request.user)
    is_night = nightmode.night_mode
  except UserProfiles.DoesNotExist:
    is_night = False
  try:
    is_upgrade, create = AccountUpgrade.objects.get_or_create(user=request.user)
  except Exception as e:
    print(e)
    return HttpResponse("Models Not Exist")
  if request.method == "POST":
    user = request.user
    pin = request.POST.get("pin")
    try:
      my_model_instance, created = GeneratePin.objects.get_or_create(user=user)
      if my_model_instance.pin == pin:
        if balance.balance >= 1000:
          with transaction.atomic():
            # Deduct balance
            balance.balance -= 1000
            balance.save()
          try:
            myup, created = AccountUpgrade.objects.get_or_create(user=user)
            myup.upgrade = True
            myup.save()
            message = "Account Successful Upgrade!!"
            return redirect("/home?upgrade=true")
          except Exception as e:
            print(e)
            return HttpResponse("User Models Not Exist")
        else:
          success = "ERROR!!"
          message = "Insufficient Balance add funds and try again"
          return redirect("/home?sufficient=false")
      else:
        message = "Incorrect Password please try again"
        return redirect("/home?pwd=false")

    except GeneratePin.DoesNotExist:
      # Handle case where MyModel does not exist
      return HttpResponse("User model does not exist")
    except Exception as e:
      return HttpResponse(f"An error occurred: {str(e)}")
  return render(request, "dashboard.html", {"nightmode":is_night, "balance": balance, "upgrade": is_upgrade, "fund": funds, "success": success, "message": message, "sufficient":sufficient, "pin":pin,"account_number":account_no, "bank":bank,"account_generate":is_generated})
  






logger = logging.getLogger(__name__)
@login_required
def generate_virtual_account(request):
    user = request.user
    try:
        account_number = PayVesselService.generate_virtual_account(user)
        return JsonResponse({'success': True, 'account_number': account_number})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)







def push_out(request):
  logout(request)
  return redirect("/accounts/login")
  
@login_required
def night_mode(request):
    try:
        # Check if the user profile exists
        user_profile = UserProfiles.objects.get(user=request.user)
        # Toggle the night_mode field
        user_profile.night_mode = not user_profile.night_mode
        user_profile.save()
        messages.success(request, "Night Mode Activated")
        return redirect("/home")
    except UserProfiles.DoesNotExist:
        try:
            # If user profile does not exist, create one
            UserProfiles.objects.create(user=request.user, night_mode=True)
            messages.success(request, "Night Mode Activated")
            return redirect("/home")
        except Exception as e:
            # Handle any exception that might occur during profile creation
            messages.error(request, "Something went wrong")
            return HttpResponse(f"An error occurred while creating the user profile: {e}")
    except Exception as e:
        # Handle any other exceptions
        messages.error(request, "Something went wrong")
        return HttpResponse(f"An error occurred: {e}")








@login_required
def purchase_data(request):
  is_night = None
  message = "Incorrect Pin please try again"
  success = "ERROR!!"
  pin = ""
  balanced = 0
  try:
    balance = Balance.objects.get(user=request.user)
    balanced = balance.balance
  except Exception:
    return HttpResponse("Something went wrong")
  try:
    x, y = GeneratePin.objects.get_or_create(user=request.user)
    pin = x.pin
  except Exception:
    messages.error("User not Exists")
    return HttpResponse("Models not exist")
  try:
    nightmode = UserProfiles.objects.get(user=request.user)
    is_night = nightmode.night_mode
  except Exception:
    is_night = False
  return render(request, "data-purchase.html", {"nightmode":is_night, "pin":pin, "message":message, "success":success, "balanced": balanced})
  
  
@login_required
def buy_bundle(request):
    
    if request.method == "POST":
        try:
            # Generate a unique transaction ID
            #unique = str(uuid.uuid4())

            # Get the current user
            user = request.user

            # Get form data
            charge = request.POST.get("amount")[1:]
            phone_number = request.POST.get("phone")
            data_amount = request.POST.get("dataType")
            dataType = request.POST.get("sme")
            service = request.POST.get("network")

            # Get user's balance
            x = Balance.objects.get(user=user)

            # Check if balance is sufficient
            if x.balance >= int(charge):
                data_process = ProcessPayment()
                user_data = data_process.process_data(service,dataType, data_amount)
                print(user_data)
                send_data = data_process.make_request(user_data, phone_number)
                print(send_data)
                if send_data["status"] == "failed":
                  messages.error(request, "Network Error. Try Again Later")
                  return redirect('/databundle')
                  
                elif (send_data["status"] == "processing"):
                  with transaction.atomic():
                    # Deduct balance
                    x.balance -= int(charge)
                    x.save()
                    dmessages = f"Purchase of {data_amount} Plan for phone number {phone_number}"
                    Transaction.objects.create(user=request.user, status=send_data["status"], message=dmessages, reference=send_data["data"]["reference"], network=send_data["data"]["network"], data_plan=send_data["data"]["dataPlan"], data_type=send_data["data"]["dataType"], amount=charge, status_code=False, balance=x)
                else:
                  with transaction.atomic():
                    # Deduct balance
                    x.balance -= int(charge)
                    x.save()

                    dmessages = f"Purchase of {data_amount} Plan for phone number {phone_number}"
                    Transaction.objects.create(user=request.user, status=send_data["status"], message=dmessages, reference=send_data["data"]["reference"], network=send_data["data"]["network"], data_plan=send_data["data"]["dataPlan"], data_type=send_data["data"]["dataType"], amount=charge, status_code=True, balance=x)
                  messages.success(request, "Successful Purchase")
                x = Transaction.objects.filter(user=user)[::-1][0]
                return redirect(f'/myreciept/{x.id}')
            else:
                messages.error(request, "Insufficient balance")
                return HttpResponse('Insufficient balance')

        except Balance.DoesNotExist:
            return HttpResponse('Balance record not found')

        except Exception as e:
            return HttpResponse(f"Error occurred: {str(e)}")

    return redirect("/home")
    
    
    
    
    
    
    
    
"""
class MyReciept(View):
    def get(self, request, id, *args, **kwargs):
        x = get_object_or_404(Development, id=id)
        old_balance = x.amount + x.balance.balance
        if request.GET.get('download'):
            # Handle the PDF download
            response = WeasyTemplateResponse(
                request=request,
                template='invoice.html',
                context={
                    'date': '2024-07-22',
                    'customer_name': 'John Doe',
                    'amount': '$100'
                },
                filename='invoice.pdf'
            )
            response.render()
            pdf = response.rendered_content

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
            return response

        # Render the initial content
        return render(request, 'reciept.html',{"reciept":x, "old":old_balance})

"""

@login_required
def myreciept(request, id):
  x = get_object_or_404(Transaction, id=id)
  old_balance = x.amount + x.balance.balance
  return render(request, "reciept.html", {"reciept":x, "old":old_balance})
  







class InvoicePDFView(WeasyTemplateView):
    template_name = 'invoice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id = kwargs.get('id')
        x = get_object_or_404(Transaction, id=id)
        old_balance = x.amount + x.balance.balance
        try:
          downloaded = Download.objects.get(user=self.request.user)
          downloaded.downloaded +=1
          downloaded.save()
          self.pdf_filename = f"reciept_pystar{downloaded.downloaded}.pdf"
        except Exception as e:
          print(e)
          Download.objects.create(user=self.request.user, downloaded=1)
          self.pdf_filename = f"reciept_pystar{1}.pdf"
        context['reciept'] = x
        context['old'] = old_balance
        return context
        






    
@login_required
def profile(request):
  success = ""
  #message to display in the templates
  message = ""
  #exist
  same_password = False
  #currentmatch
  old_password = False
  #to handle both sucessful and check new password with retype password 
  ischange = False
  is_password_match = False
  try:
    check = request.GET.get("ischange")
    if check == "true":
      ischange = True
      message = "Password successfully change"
      success = "Successful"
    elif check == "false":
      is_password_match  = True
      message = "New Password is not match with confirm password"
      success = "ERROR!!"
    else:
      ischange = False
  except Exception:
    print("ischange not available")
    
  try:
    check = request.GET.get("currentmatch")
    if check == "false":
      old_password = True
      message = "Password not match with the old password"
      success = "ERROR!!"
    else:
      old_password  = False
  except Exception:
    print("ischange not available")
    
  try:
    check = request.GET.get("exist")
    if check == "true":
      same_password = True
      message = "Cannot use same password"
      success = "ERROR!!"
    else:
      same_password  = False
  except Exception:
    print("ischange not available")
  try:
    profiles, created = Profile.objects.get_or_create(user=request.user)
  except Profile.DoesNotExist:
    return HttpResponse("Models not exists")
  except Exception as e:
    return HttpResponse(f"Error occurred: {e}")
    
  is_night, create_night = UserProfiles.objects.get_or_create(user=request.user)
  return render(request, "profile.html", {"profile":profiles, "message": message, "ischange": ischange, "old_password": old_password, "same_password": same_password, "is_match": is_password_match, "success":success, "nightmode":is_night})
  
  
  
  
  
  
  
  
  
@login_required
@require_POST
def change_password(request):
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    user = request.user
    
    if (new_password != confirm_password) and len(new_password) >= 2:
      messages.error(request, "Password not match")
      return redirect("/profile?ischange=false")
    
    if user.check_password(new_password):
      messages.error("Cannot use same password")
      return redirect("/profile?exist=true")
    # Check the current password
    if not user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
        return redirect('/profile?currentmatch=false')  # Redirect to the password change page
    
    # Set and save the new password
    user.set_password(new_password)
    user.save()
    
    # Update the session to prevent logout
    update_session_auth_hash(request, user)
    
    messages.success(request, "Password changed successfully.")
    return redirect('/profile?ischange=true')  # Redirect to a success page


def change_pin(request):
  list(messages.get_messages(request))
  if request.method == "POST":
    try:
      mypin, crt = GeneratePin.objects.get_or_create(user=request.user)
      new_pin = request.POST.get("newpin")
      oldpin = request.POST.get("oldpin")
      confirm_pin = request.POST.get("retypepin")
      if new_pin != confirm_pin:
        messages.error(request, "Password not match")
        return redirect("/profile")
        
      if oldpin != mypin.pin:
        messages.error(request, "Old Password Not Match")
        return redirect("/profile")
      if new_pin == mypin.pin:
        messages.error(request, "Cannot use same passworď")
        return redirect("/profile")
        
      mypin.pin = new_pin
      mypin.save()
      messages.success(request, "Pin successfully changed")
      return redirect(reverse("profile"))
    except Exception as e:
      print("something went wrong", e)
      return HttpResponse("Something Went Wrong")
  else:
    return redirect("/profile")
    


class SearchResultsView(ListView):
  model = Transaction
  template_name = 'transaction.html'
  context_object_name = 'dev'

  def get_queryset(self):
    query = self.request.GET.get('q')
    if query:
      result = Transaction.objects.filter(Q(message__icontains=query)|Q(data_plan__icontains=query)|Q(amount__icontains=query), user=self.request.user)
      return result.order_by('-id')
    return Transaction.objects.none()
    
  def get_context_data(self, **kwargs):
    is_night = None
    try:
      nightmode = UserProfiles.objects.get(user=self.request.user)
      is_night = nightmode.night_mode
    except Exception:
      is_night = False
      print('Something went wrong')
    context = super().get_context_data(**kwargs)
    # Add your additional data here
    context['nightmode'] = is_night
    # For example, you might want to pass a count of results
    context['total_results'] = self.get_queryset().count()
    return context
    
    
    
@require_POST
@csrf_exempt
def payvessel_payment_done(request):
        payload = request.body
        payvessel_signature = request.META.get('HTTP_PAYVESSEL_HTTP_SIGNATURE')
        
        #this line maybe be differ depends on your server
        #ip_address = u'{}'.format(request.META.get('HTTP_X_FORWARDED_FOR'))
        ip_address = u'{}'.format(request.META.get('REMOTE_ADDR'))
        secret = bytes("PVSECRET-", 'utf-8')
        hashkey = hmac.new(secret,request.body, hashlib.sha512).hexdigest()
        ipAddress = ["3.255.23.38", "162.246.254.36"]
        if payvessel_signature == hashkey  and ip_address in ipAddress:
                data = json.loads(payload)
                amount = float(data['order']["amount"])
                settlementAmount = float(data['order']["settlement_amount"])
                fee = float(data['order']["fee"])
                reference = data['transaction']["reference"]
                description = data['order']["description"]
                settlementAmount = settlementAmount 
                fees = fee
                settle_amount = settlementAmount
                ###check if reference already exist in your payment transaction table 
                if not WalletFunding.objects.filter(transaction_reference=reference).exists():
                   if (amount > 3000):
                     fees = fees+50
                     settle_amount = settle_amount - 50
                   else:
                     fees = fees+25
                     settle_amount = settle_amount - 25
                   WalletFunding.objects.create(user=request.user, fund_amount=amount, settle_amount=settle_amount, fees=fees, transaction_reference=reference,description=description, status=True, header="Account Fund")
                   #fund user wallet here
                   balance, created = Balance.objects.get_or_create(user=request.user)
                   balance.balance = balance.balance + settle_amount
                   balance.save()
                   
                   return JsonResponse({"message": "success",},status=200) 
                        
                else:
                    return JsonResponse({"message": "transaction already exist",},status=200) 
        
        else:
            return JsonResponse({"message": "Permission denied, invalid hash or ip address.",},status=400) 
            
            

  