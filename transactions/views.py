from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Transaction
from .forms import TransactionForm
from decimal import Decimal


# Create your views here.
@login_required
def transaction_list(request):
    sort = request.GET.get("sort", "-date")  # default newest first

    # Whitelist allowed sort fields (security best practice)
    allowed_sorts = [
        "date", "-date",
        "type", "-type",
        "category", "-category",
        "amount", "-amount",
    ]

    if sort not in allowed_sorts:
        sort = "-date"

    transactions = (
        Transaction.objects
        .filter(user=request.user)
        .order_by(sort)
    )

    context = {
        "transactions": transactions,
        "current_sort": sort,
    }

    return render(request, "transactions/transaction_list.html", context)


@login_required
def transaction_create(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect("transactions:list")
    else:
        form = TransactionForm()

    return render(request, "transactions/transaction_form.html", {"form": form, "title": "Add Transaction"})


@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == "POST":
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect("transactions:list")
    else:
        form = TransactionForm(instance=transaction)

    return render(request, "transactions/transaction_form.html", {"form": form, "title": "Edit Transaction"})


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == "POST":
        transaction.delete()
        return redirect("transactions:list")

    return render(request, "transactions/transaction_confirm_delete.html", {"transaction": transaction})


@login_required
def dashboard(request):
    # month format: YYYY-MM
    month = request.GET.get("month")

    qs = Transaction.objects.filter(user=request.user)

    if month:
        # filter by prefix on date string-like "YYYY-MM"
        try:
            year_str, month_str = month.split("-")
            year = int(year_str)
            month_num = int(month_str)
            qs = qs.filter(date__year=year, date__month=month_num)
        except ValueError:
            month = None  # ignore bad input

    # Totals
    income_total = qs.filter(type="income").aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    expense_total = qs.filter(type="expense").aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    net = income_total - expense_total

    # Build month options from user's transactions (unique YYYY-MM)
    all_dates = Transaction.objects.filter(user=request.user).values_list("date", flat=True).order_by("-date")
    month_options = []
    seen = set()
    for d in all_dates:
        key = d.strftime("%Y-%m")
        if key not in seen:
            month_options.append(key)
            seen.add(key)

    # Category totals (income + expense)
    income_by_category = (
        qs.filter(type="income")
          .values("category")
          .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
          .order_by("-total")
    )

    expense_by_category = (
        qs.filter(type="expense")
          .values("category")
          .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
          .order_by("-total")
    )


    context = {
        "month": month,
        "month_options": month_options,
        "income_total": income_total,
        "expense_total": expense_total,
        "net": net,
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
    }
    return render(request, "transactions/dashboard.html", context)
