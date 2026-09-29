# Manual de Usuario — Maestros de Transser One

Guía para el equipo de Transser sobre cómo usar el módulo **Maestros** del ERP: los catálogos base (clientes, tarifas, flota, ubicaciones) que alimentan el resto del sistema.

---

## 1. Cómo entrar

1. Abre la URL del sistema en tu navegador (en ambiente local: `http://localhost:8001`).
2. Ingresa tu correo corporativo y contraseña.
3. Si tu cuenta está bloqueada temporalmente (5 intentos fallidos), espera 15 minutos e inténtalo de nuevo.

**Cuentas de referencia en ambiente de desarrollo** (creadas con `python manage.py seed_demo`, contraseña `Transser2026!` para las tres):

| Correo | Rol |
|---|---|
| jorge@transser.cl | Administrador |
| alan@transser.cl | Operaciones |
| christian@transser.cl | Gerencia |

> En producción cada persona debe tener su propia cuenta — pídele a un Administrador que te cree la tuya.

---

## 2. Navegación general

El menú de la izquierda tiene:

- **Dashboard**: resumen ejecutivo de ventas y servicios.
- **Centro de Operaciones**: listado y seguimiento de viajes.
- **Nuevo Servicio**: crear una orden de transporte.
- **Maestros**: 👈 este módulo — todos los catálogos base.
- **Flota** / **Conductores**: accesos directos a los mantenedores de tractos y choferes.
- **Finanzas / Reportes**: en construcción.

---

## 3. El módulo Maestros

Al entrar a **Maestros** ves las 16 tablas agrupadas en 4 categorías:

| Grupo | Qué contiene |
|---|---|
| 💼 **Comercial** | Clientes, Locales, Tarifas, Formas de pago |
| 🚛 **Flota** | Ramplas, Tractos, Conductores |
| 🗺️ **Ubicación** | Rutas, Comunas, Regiones |
| 🗂️ **Catálogos** | Proveedores, Centros de costo, Prioridades, Tipos de servicio, Tipos de tarifa, Tipos de rampla |

Cada tarjeta muestra cuántos registros tiene esa tabla hoy. Haz clic en cualquiera para entrar a su mantenedor.

### 3.1 Cómo usar cualquier mantenedor

Todos los mantenedores funcionan igual, así que aprender uno es aprender los 16:

- **Ver la lista**: al entrar ves todos los registros en una tabla.
- **Buscar**: usa el buscador arriba a la derecha (busca por los campos más relevantes de esa tabla, ej. nombre o RUT).
- **Crear**: botón naranja "+ Nuevo…" arriba a la derecha. Completa el formulario y presiona **Guardar**.
- **Editar**: botón "Editar" en la fila del registro.
- **Eliminar**: botón "Eliminar" en la fila — te pide confirmación antes de borrar.
  - Si el registro está siendo usado por otro (ej. quieres borrar un Cliente que tiene Locales o Tarifas asociadas), el sistema **no lo deja eliminar** y muestra un mensaje de error. Esto es intencional: protege la trazabilidad — primero hay que borrar o reasignar lo que depende de ese registro.

### 3.2 Qué significan los indicadores en las tablas

- **Pill verde "Activo"/"Activa"**: el registro está vigente y disponible para usarse en el resto del sistema.
- **Pill gris "Inactivo"/"Inactiva"**: el registro existe (por historial) pero no debería usarse en operaciones nuevas.
- **Texto en recuadro gris** (ej. una patente o un RUT): son datos tipo código, se muestran en fuente distinta para que sean fáciles de leer.
- **Guion "—"**: el campo está vacío.

---

## 4. Guía por catálogo

### Clientes
La marca dueña de la carga que le paga a Transser (ej. Walmart, Cencosud, Sodimac) — **no** el transportista subcontratado, eso va en Proveedores.
Campos: razón social, giro, RUT, dirección, contacto, ejecutivo comercial a cargo, cupo de crédito.

### Locales
Las tiendas/sucursales de un Cliente donde se carga o descarga (ej. "Plaza Lyon", formato "Express"). Cada Local pertenece a un Cliente y a una Comuna.

### Tarifas
El valor acordado con un Cliente para una Ruta y un Tipo de tarifa determinados. Si cargas el **costo** además del valor de venta, el sistema calcula automáticamente el **profit** (utilidad) — no hace falta calcularlo a mano.

### Formas de pago
Métodos de pago aceptados (transferencia, cheque, etc.) con espacio para observaciones.

### Ramplas
Los remolques de la flota. Marca si una rampla **es externa** (de un proveedor, no propia) y a qué Proveedor pertenece.

### Tractos
Los camiones tracto: patente, marca, modelo, TAG de telepeaje, tarjeta de combustible, proveedor de GPS y estado.

### Conductores
Los choferes: nombre, RUT, teléfono, dirección, fecha de ingreso y tipo de contrato.

### Rutas
Combinación de Comuna origen → Comuna destino, con los kilómetros. Se reutiliza al crear Tarifas.

### Comunas / Regiones
Geografía base de Chile. Crea primero la Región, luego la Comuna asociada a esa Región.

### Proveedores
Transportistas o terceros subcontratados que prestan servicios a Transser (ej. Fernandez, Agudi, Barz).

### Centros de costo, Prioridades, Tipos de servicio, Tipos de tarifa, Tipos de rampla
Catálogos simples de referencia (solo nombre y, en algunos, una descripción/orden) que se usan como listas desplegables en el resto del sistema. Mantenlos limpios: evita crear "Seco" y "seco" como dos registros distintos.

---

## 5. Preguntas frecuentes

**¿Por qué no puedo elegir una Comuna al crear un Local si no aparece en la lista?**
Porque todavía no existe esa Comuna en el catálogo. Ve a Maestros → Comunas → Nueva comuna y créala (necesitas que su Región ya exista).

**Cargué mal un dato, ¿puedo editarlo?**
Sí, botón "Editar" en la fila. Los cambios quedan guardados de inmediato.

**Borré algo por error.**
Si alcanzaste a confirmar la eliminación, no hay deshacer desde la pantalla — avisa a un Administrador para restaurarlo desde una copia de respaldo de la base de datos.

**¿Los datos del Excel se cargan solos?**
No todavía — hoy se cargan a mano desde cada mantenedor. La carga masiva desde Excel es un paso pendiente (ver el resumen técnico).

---

## 6. Qué viene después

- Carga de los datos reales (clientes, locales, tarifas, flota) desde el Excel de la empresa.
- Conectar estos catálogos a la creación de un Servicio (hoy el formulario de "Nuevo Servicio" todavía usa texto libre).
- Módulo de Facturación y Cobranza.
