from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


def login_view(request):
    if request.method == "GET" and request.user.is_authenticated:
        return redirect("operaciones:dashboard")

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        usuario = authenticate(request, username=email, password=password)
        if usuario is not None and usuario.is_active:
            login(request, usuario)
            destino = request.GET.get("next") or "operaciones:dashboard"
            return redirect(destino)
        error = "Correo o contraseña incorrectos, o cuenta bloqueada temporalmente por demasiados intentos."

    return render(request, "accounts/login.html", {"error": error})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")
