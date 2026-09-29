/**
 * Validación de RUT chileno (dígito verificador módulo 11) para los
 * formularios de Transser One.
 *
 * Se engancha a cualquier <input> cuyo name sea "rut" o tenga ese patrón
 * (rut_vendedor, rut_conductor, etc.) — Clientes, Proveedores, Conductores
 * hoy, y cualquier mantenedor nuevo con un campo así, sin tocar este
 * archivo. Si el formulario no tiene ninguno, no hace nada.
 *
 * Mientras el RUT no sea válido: se muestra un mensaje bajo el campo y
 * el botón "Guardar" queda deshabilitado.
 */
(function () {
  "use strict";

  function limpiarRut(valor) {
    return (valor || "").replace(/[^0-9kK]/g, "").toUpperCase();
  }

  function formatearRut(valor) {
    const limpio = limpiarRut(valor);
    if (limpio.length < 2) return limpio;
    const cuerpo = limpio.slice(0, -1).replace(/^0+(?=\d)/, "");
    const dv = limpio.slice(-1);
    const cuerpoFormateado = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return `${cuerpoFormateado}-${dv}`;
  }

  function calcularDv(cuerpo) {
    let suma = 0;
    let multiplicador = 2;
    for (let i = cuerpo.length - 1; i >= 0; i--) {
      suma += parseInt(cuerpo[i], 10) * multiplicador;
      multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
    }
    const resto = 11 - (suma % 11);
    if (resto === 11) return "0";
    if (resto === 10) return "K";
    return String(resto);
  }

  function rutValido(valor) {
    const limpio = limpiarRut(valor);
    if (limpio.length < 2) return false;
    const cuerpo = limpio.slice(0, -1);
    const dv = limpio.slice(-1);
    if (!/^\d{1,8}$/.test(cuerpo)) return false;
    return calcularDv(cuerpo) === dv;
  }

  function mensajeDe(input) {
    let mensaje = input.parentElement.querySelector(".rut-mensaje");
    if (!mensaje) {
      mensaje = document.createElement("span");
      mensaje.className = "warning-text rut-mensaje";
      input.insertAdjacentElement("afterend", mensaje);
    }
    return mensaje;
  }

  function validarCampo(input, formatear) {
    const mensaje = mensajeDe(input);
    const valor = input.value.trim();
    const requerido = input.hasAttribute("required");

    if (!valor) {
      input.setCustomValidity(requerido ? "El RUT es obligatorio." : "");
      mensaje.textContent = "";
      return !requerido;
    }
    if (!rutValido(valor)) {
      input.setCustomValidity("RUT inválido.");
      mensaje.textContent = "RUT inválido — revisa el número o el dígito verificador.";
      return false;
    }
    input.setCustomValidity("");
    mensaje.textContent = "";
    if (formatear) input.value = formatearRut(valor);
    return true;
  }

  function iniciarValidacionRut(form) {
    if (form.dataset.rutValidado) return; // no re-enganchar el mismo form
    // Cualquier input cuyo name sea "rut" o termine en "_rut"/empiece con
    // "rut_" (ej. rut_vendedor, rut_conductor) se valida igual.
    const campos = form.querySelectorAll(
      'input[name="rut"], input[name$="_rut"], input[name^="rut_"]'
    );
    if (!campos.length) return;
    form.dataset.rutValidado = "1";

    const boton = form.querySelector('button[type="submit"]');

    function actualizarBoton(formatear) {
      // OJO: .map() (no .every) — cada campo se tiene que validar siempre,
      // aunque uno anterior ya haya salido inválido, o si no el mensaje/
      // formato del resto de los campos de RUT nunca se actualiza.
      const resultados = Array.from(campos).map((c) => validarCampo(c, formatear));
      const todosValidos = resultados.every(Boolean);
      if (boton) boton.disabled = !todosValidos;
      return todosValidos;
    }

    campos.forEach((input) => {
      input.addEventListener("input", () => actualizarBoton(false));
      input.addEventListener("blur", () => actualizarBoton(true));
    });

    actualizarBoton(true);

    form.addEventListener("submit", (evento) => {
      if (!actualizarBoton(true)) {
        evento.preventDefault();
      }
    });
  }

  function iniciarTodos(raiz) {
    raiz.querySelectorAll("form").forEach(iniciarValidacionRut);
  }

  document.addEventListener("DOMContentLoaded", () => iniciarTodos(document));
  // Los formularios que llegan vía htmx (fragmentos re-renderizados) también quedan cubiertos.
  document.body.addEventListener("htmx:afterSwap", (evento) => iniciarTodos(evento.detail.target));
})();
