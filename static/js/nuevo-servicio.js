/**
 * "Nuevo Servicio": actualiza Neto/IVA/Total apenas se elige el tipo de
 * tarifa (seco/frío/congelado/única). El valor de cada opción ya viene
 * en el fragmento htmx (data-valor), así que esto es puramente visual —
 * no hace falta otro viaje al servidor. El servidor igual vuelve a
 * calcular todo desde cero al guardar (nunca confía en este cálculo).
 */
(function () {
  "use strict";

  function formatearCLP(numero) {
    return "$" + Math.round(numero).toLocaleString("es-CL");
  }

  function actualizarPreview(select) {
    const opcion = select.options[select.selectedIndex];
    const valor = parseFloat(opcion && opcion.dataset.valor) || 0;
    const iva = valor * 0.19;
    const total = valor + iva;

    const neto = document.getElementById("tarifa-neto");
    const ivaEl = document.getElementById("tarifa-iva");
    const totalEl = document.getElementById("tarifa-total");
    if (neto) neto.textContent = formatearCLP(valor);
    if (ivaEl) ivaEl.textContent = formatearCLP(iva);
    if (totalEl) totalEl.textContent = formatearCLP(total);
  }

  document.body.addEventListener("change", (evento) => {
    if (evento.target && evento.target.id === "tipo_tarifa_select") {
      actualizarPreview(evento.target);
    }
  });

  // Cuando htmx trae un #tarifa-preview nuevo (cambió cliente/local/ruta),
  // si ya trae un tipo de tarifa preseleccionado, refleja su valor.
  document.body.addEventListener("htmx:afterSwap", (evento) => {
    const select = evento.detail.target.querySelector && evento.detail.target.querySelector("#tipo_tarifa_select");
    if (select && select.value) actualizarPreview(select);
  });
})();
