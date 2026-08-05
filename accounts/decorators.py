from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """Exige sesión iniciada Y que el usuario pertenezca a alguno de los
    grupos (roles) indicados. Equivalente a rol_es/rol_en de
    backend/app/authz.py en el sistema FastAPI."""

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltorio(request, *args, **kwargs):
            if not request.user.groups.filter(name__in=roles).exists():
                raise PermissionDenied(f"Esta acción requiere el rol: {' o '.join(roles)}.")
            return vista(request, *args, **kwargs)

        return envoltorio

    return decorador
