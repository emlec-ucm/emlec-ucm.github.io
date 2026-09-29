# Correos a los participantes de The Computational Garage

Guía para quienes tienen permisos en este repositorio. Explica qué correos se
envían, cuándo, y cómo enviar uno a mano.

Todos los correos salen desde la cuenta de Gmail del grupo (secret `EMAIL_USER`)
a la lista de participantes (secret `EMAIL_RECIPIENTS`), siempre en **copia
oculta**: ningún participante ve las direcciones de los demás.

## Tipos de mensajes

| Mensaje | Cómo se envía | Dónde |
|---|---|---|
| **Nueva sesión** (aviso con fecha, hora, ponente y lugar) | Automático, al añadir la sesión en `sesiones.org` y hacer push | Sección 1 |
| **Recordatorio** ("mañana hay sesión") | Automático, cada mañana si hay sesión al día siguiente | Sección 1 |
| **Mensaje general** (cualquier aviso: cambio de aula, cancelación, convocatoria de ponentes...) | A mano, redactándolo como issue | Sección 2 |
| **Reenvío manual** del aviso de nueva sesión o del recordatorio de la próxima sesión | A mano, desde un issue (con el paso de prueba y archivo) o desde Actions (dos clics, sin prueba) | Secciones 2 y 3 |

---

## 1. Qué se envía automáticamente

| Correo | Cuándo | Cómo se decide |
|---|---|---|
| **Nueva sesión** | Al hacer push a `main` | Se compara `content/TheComputationalGarage/sesiones.org` con el estado anterior al push. Por cada sesión **nueva con fecha futura** se envía un aviso. Añadir sesiones pasadas o corregir textos no envía nada. |
| **Recordatorio** | Cada mañana (cron a las 05:00 UTC, es decir, entre las 7 y las 9 hora de Madrid según el retraso de GitHub) | Solo si hay una sesión programada **para mañana**. |

Los datos de la sesión (fecha, hora, ponentes, lugar) se toman de `sesiones.org`:

```org
** 2026-05-12
   :PROPERTIES:
   :SCHEDULED: <2026-05-12 Tue 11:30>
   :SPEAKERS: Nombre del ponente
   :LOCATION: Aula 302, Pabellón de Primero
   :END:

   - *Ponentes:* Nombre del ponente
   - *Hora:* 11:30
   - *Lugar:* Aula 302, Pabellón de Primero
```

La fecha se lee del título (`** YYYY-MM-DD`), ponentes y lugar de las
propiedades `SPEAKERS` y `LOCATION`, y la hora de la línea `*Hora:*` (o, si
falta, de `SCHEDULED`).

---

## 2. Enviar un mensaje desde un issue

Es el procedimiento general para cualquier envío manual. El mensaje se redacta
como un *issue* de GitHub y se envía poniéndole una etiqueta. Sirve para tres
tipos de correo, que se eligen en el desplegable **Tipo de mensaje** del
formulario:

- **Mensaje general**: cualquier aviso (cambio de aula, cancelación,
  convocatoria de ponentes...). Escribes tú el asunto y el cuerpo.
- **Recordatorio de la próxima sesión**: el correo de recordatorio de siempre,
  generado con los datos de la próxima sesión programada en `sesiones.org`.
- **Aviso de nueva sesión**: el correo de "nueva sesión", generado igual.

Pasos:

1. Ve a **Issues → New issue** y elige la plantilla **"Mensaje a los participantes"**.
2. Elige el **Tipo de mensaje**.
3. Para el **mensaje general**, escribe el asunto en el **título** después de
   `[Mensaje]` (ejemplo: `[Mensaje] Cambio de aula para la sesión de octubre`)
   y el cuerpo en **Mensaje**. Admite Markdown (negritas, listas, enlaces); la
   pestaña *Preview* muestra cómo quedará. No hace falta firmar: la firma del
   grupo se añade sola al final. Si quieres que el correo incluya los datos de
   la próxima sesión programada, marca la casilla de **Opciones**.
4. Para el **recordatorio** o el **aviso de nueva sesión**, el asunto y el
   cuerpo se generan solos y el título del issue no se usa. El campo
   **Mensaje** es opcional: si escribes algo, se añade como párrafo después de
   los datos de la sesión (por ejemplo, "esta vez empezamos a las 12:00"). Si
   no hay ninguna sesión futura en `sesiones.org`, el envío falla y lo indica
   en un comentario del issue.
5. Pulsa **Submit new issue**. **Esto no envía nada todavía.**
6. Para revisar el correo, añade al issue la etiqueta **`prueba`**: en unos
   segundos llega solo a la cuenta de Gmail del grupo
   (`thecomputationalgarage@gmail.com`, no a tu dirección personal), y el
   issue recibe un comentario confirmándolo. Puedes editar el issue y repetir
   la prueba.
7. Para enviarlo a todos, añade la etiqueta **`enviar`**. El issue recibe un
   comentario con la hora del envío y se cierra automáticamente.

**Dónde se ponen las etiquetas.** Las etiquetas se eligen en el menú
desplegable **Labels** que hay en la última fila de la ventana de edición del
issue (o, en la vista clásica, en la columna de la derecha de la página del
issue). Se pueden poner al crear el issue o en cualquier momento después,
abriendo el issue y pulsando en ese menú.

Los issues cerrados con la etiqueta `mensaje` son el archivo de todo lo enviado.

**Seguridad.** Cualquiera puede abrir un issue en un repositorio público,
pero solo quien tiene permisos (triage o superior) puede poner etiquetas. El
workflow comprueba además, vía API, el permiso de quien puso la etiqueta, que
el issue está abierto y que tiene la etiqueta `mensaje` (es decir, que se creó
con la plantilla). Si algo no cuadra, lo explica en el log y en un comentario
del issue.

**Si falla**, el issue recibe un comentario con el enlace al log y se retira la
etiqueta. Corrige lo necesario y vuelve a ponerla.

---

## 3. Reenviar un anuncio o recordatorio desde Actions

Alternativa rápida al issue para el recordatorio y el aviso de nueva sesión:
dos clics, pero sin paso de prueba previo y sin archivo (solo queda el log del
run). Ambos caminos conviven; usa el que prefieras.

1. Ve a **Actions → Send Email Notification → Run workflow**.
2. Elige el tipo:
   - **reminder**: recordatorio de la próxima sesión programada.
   - **announcement**: aviso de "nueva sesión" para la próxima sesión programada.
3. Marca **Modo prueba** si quieres que llegue solo a la cuenta del grupo.
4. Pulsa **Run workflow**.

"Próxima sesión programada" es la de fecha más cercana igual o posterior a hoy.
Si no hay ninguna, no se envía nada y el log lo indica.

---

## 4. Modificar la lista de destinatarios

1. **Settings → Secrets and variables → Actions**.
2. **EMAIL_RECIPIENTS → Update secret**.
3. Escribe las direcciones separadas por comas (los espacios se ignoran).
4. **Update secret**.

---

## 5. Cómo está montado

| Fichero | Función |
|---|---|
| `scripts/tcg_mail.py` | Único script de correo. Subcomandos `announce`, `remind` y `message`. Opciones comunes `--test` (solo a la cuenta del grupo) y `--dry-run` (no envía; muestra el correo). |
| `.github/workflows/publish.yml` | Genera la web al hacer push y ejecuta `announce --base <commit anterior>`. |
| `.github/workflows/send-notification.yml` | Cron diario (`remind --if-tomorrow`) y ejecución manual (`remind` o `announce --force`). Incluye un paso *keepalive* (ver abajo). |
| `.github/workflows/send-message.yml` | Envía el contenido de un issue al etiquetarlo con `prueba` o `enviar`. |
| `.github/ISSUE_TEMPLATE/mensaje.yml` | Formulario del issue "Mensaje a los participantes". |

Secrets necesarios: `EMAIL_USER` (Gmail del grupo), `EMAIL_PASSWORD`
(contraseña de aplicación de 16 caracteres) y `EMAIL_RECIPIENTS`.

**Keepalive.** GitHub desactiva los workflows con cron en repositorios públicos
tras 60 días sin commits (ocurrió en julio de 2026). El workflow del cron hace
ahora un commit vacío cuando el repositorio lleva 50 días sin actividad; ese
commit no regenera la web ni envía correos. Si aun así el workflow apareciese
como *disabled* en Actions, basta con abrirlo y pulsar **Enable workflow**.

Para probar el script en local sin enviar nada:

```bash
EMAIL_USER=x EMAIL_PASSWORD=x EMAIL_RECIPIENTS=a@ucm.es \
  python3 scripts/tcg_mail.py remind --dry-run
```

---

## 6. Solución de problemas

- **Un run en rojo.** El script falla (código 1) cuando faltan secrets o el
  envío SMTP da error, para que se vea. Abre el run en Actions y busca la línea
  `::error::` o `[ERROR]`.
- `Error SMTP ... (535, ...)`: contraseña de aplicación incorrecta o revocada.
  Genera otra en la cuenta de Gmail (Seguridad → Verificación en dos pasos →
  Contraseñas de aplicaciones) y actualiza `EMAIL_PASSWORD`.
- `No hay sesiones nuevas con fecha futura`: el push no añadió sesiones con
  fecha posterior a hoy; es lo normal en la mayoría de los pushes.
- **El cron no se ejecuta.** Comprueba en Actions que "Send Email
  Notification" no está desactivado (ver *Keepalive*).
- **Límites de Gmail:** 500 correos al día y 100 destinatarios por mensaje (el
  script parte la lista en bloques de 80 si hiciera falta).
