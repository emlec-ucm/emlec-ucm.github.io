# Correos a los participantes de The Computational Garage

Guía para quienes tienen permisos en este repositorio. Explica qué correos se
envían, cuándo, y cómo enviar uno a mano.

Todos los correos salen desde la cuenta de Gmail del grupo (secret `EMAIL_USER`)
a la lista de participantes (fichero cifrado `content/TheComputationalGarage/gente`,
ver sección 4), siempre en **copia oculta**: ningún participante ve las
direcciones de los demás.

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

Es el procedimiento general para cualquier envío manual: el correo se prepara
como un *issue* de GitHub y se envía poniéndole una etiqueta. Con la plantilla
se pueden mandar tres tipos de correo, que se eligen en el desplegable **Tipo
de mensaje**. Los pasos son distintos según el tipo; están en 2.1 y 2.2.

> **Importante: todo lo que se escribe en un issue es público.** Este
> repositorio es público, así que el issue, sus comentarios y su historial de
> ediciones pueden leerse desde cualquier sitio de Internet, sin cuenta de
> GitHub, y los buscadores los indexan. Cerrar el issue no lo oculta: los
> issues cerrados siguen siendo visibles (y por eso sirven de archivo). El
> asunto del correo aparece también en el log de la ejecución, que es
> igualmente público. Escribe solo lo que pudiera leer una tercera persona:
> nada de datos personales de participantes, ni valoraciones, ni información
> interna del departamento. Si un mensaje ya enviado no debe quedar a la
> vista, un administrador puede borrar el issue (menú "..." del issue →
> *Delete issue*); desaparece del archivo.

### 2.1 Mensaje general (texto libre)

Para cualquier aviso: cambio de aula, cancelación, convocatoria de ponentes...

1. Ve a **Issues → New issue** y elige la plantilla **"Mensaje a los participantes"**.
2. En **Tipo de mensaje**, deja **"Mensaje general"** (es la opción por defecto).
   En **Destinatarios**, elige a quién va: todos los participantes (por
   defecto), senior (que incluye siempre a los jefes), solo jefes o solo
   junior. Los grupos son los del fichero de participantes (sección 4).
3. En el **título**, escribe el asunto del correo después de `[Mensaje]`.
   Ejemplo: `[Mensaje] Cambio de aula para la sesión de octubre`.
4. En **Mensaje**, escribe el cuerpo. Admite Markdown (negritas, listas,
   enlaces); la pestaña *Preview* muestra cómo quedará. No hace falta firmar:
   la firma del grupo se añade sola al final.
5. Si quieres que el correo termine con los datos de la próxima sesión
   programada, marca la casilla de **Opciones**.
6. Añade la etiqueta **`prueba`** (ver *Dónde se ponen las etiquetas*, más
   abajo) y pulsa **Submit new issue**. En unos segundos el correo llega
   **solo a la cuenta de Gmail del grupo** (`thecomputationalgarage@gmail.com`,
   no a tu dirección personal) y el issue recibe un comentario confirmándolo.
   Si quieres cambiar algo, edita el issue y vuelve a poner `prueba`.
7. Cuando esté bien, añade la etiqueta **`enviar`**. El correo sale a los
   destinatarios elegidos en el paso 2, el issue recibe un comentario con la
   hora del envío y se cierra solo.

Si prefieres no hacer prueba, puedes poner `enviar` directamente en el paso 6.

**Qué dicen los comentarios del issue.** Tras la prueba, el comentario indica
a quién irá el correo cuando pongas `enviar`; tras el envío, a quién ha ido.
El número de direcciones es el real, contado tras descifrar la lista:

| Destinatarios elegidos | Texto del comentario (recuentos de ejemplo) |
|---|---|
| Todos los participantes | ✅ **Prueba enviada** (29/09/2026 10:55) solo a la cuenta de correo del grupo. Revísala y, si está bien, añade la etiqueta **enviar** para mandarla a sus destinatarios: **todos los participantes** (23 direcciones). |
| Senior (incluye a los jefes) | … para mandarla a sus destinatarios: **senior (incluidos los jefes)** (8 direcciones). |
| Solo jefes | … para mandarla a sus destinatarios: **solo los jefes** (3 direcciones). |
| Solo junior | … para mandarla a sus destinatarios: **solo los junior** (15 direcciones). |

Y tras poner `enviar`, por ejemplo: ✅ **Mensaje enviado** (29/09/2026 11:02)
a **senior (incluidos los jefes)** (8 direcciones).

### 2.2 Recordatorio de la próxima sesión, o aviso de nueva sesión

Son los mismos correos que se envían automáticamente (sección 1), generados
con los datos de la próxima sesión programada en `sesiones.org`. Sirven para
repetir el aviso o mandar un recordatorio fuera del cron. No hay que escribir
nada: ni asunto ni cuerpo.

1. Ve a **Issues → New issue** y elige la plantilla **"Mensaje a los participantes"**.
2. En **Tipo de mensaje**, elige **"Recordatorio de la próxima sesión"** o
   **"Aviso de nueva sesión"**. En **Destinatarios**, normalmente "Todos".
3. Deja el **título** tal cual (`[Mensaje] `): en estos dos tipos no se usa.
4. Deja el campo **Mensaje** vacío. Si escribes algo, se añade al correo como
   párrafo después de los datos de la sesión (por ejemplo, "esta vez
   empezamos a las 12:00").
5. Añade la etiqueta **`prueba`** y pulsa **Submit new issue**. El correo
   llega solo a la cuenta de Gmail del grupo, y el issue recibe un comentario
   confirmándolo.
6. Cuando esté bien, añade la etiqueta **`enviar`**. Sale a los destinatarios
   elegidos y el issue se cierra solo. Los comentarios del issue indican a
   quién va, igual que en 2.1.

"Próxima sesión programada" es la de fecha más cercana igual o posterior a
hoy. Si no hay ninguna en `sesiones.org`, el envío falla y el issue recibe un
comentario indicándolo.

El mismo resultado se consigue desde Actions (sección 3), sin paso de prueba.

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

## 4. La lista de participantes

La lista vive en el fichero `content/TheComputationalGarage/gente`, un fichero
org con una entrada cifrada con **org-crypt** (cifrado simétrico). La frase de
paso está guardada en el secret `GENTE_PASSPHRASE`; con ella, los workflows
descifran el fichero en cada envío. No hay ninguna otra copia de la lista.

Estructura del contenido cifrado: un subencabezado por grupo y, debajo, una
dirección por línea. Las comas, los nombres y las líneas que empiezan por `#`
se ignoran (sirve para dejar a alguien apuntado sin que reciba correos).

```org
* Lista :crypt:
** Jefes
   nombre1@ucm.es,
** Senior
   nombre2@ucm.es,
   # nombre3@ucm.es,   <- de baja temporal: no recibe correos
** Junior
   nombre4@ucm.es,
```

Destinatarios posibles en los envíos: **todos** (los tres grupos), **senior**
(Senior más Jefes), **jefes** y **junior**. Los correos automáticos van
siempre a todos. Si se añade un grupo nuevo en el fichero, hay que añadir la
opción en el formulario del issue (`.github/ISSUE_TEMPLATE/mensaje.yml`) y en
`AUDIENCES` de `scripts/tcg_mail.py`.

**Añadir o quitar a alguien**, desde Emacs:

1. Abre `content/TheComputationalGarage/gente`.
2. Sitúate en la entrada `* Lista` y ejecuta `M-x org-decrypt-entry` (pide la
   frase de paso).
3. Edita las direcciones.
4. Guarda: org-crypt vuelve a cifrar la entrada automáticamente al guardar.
   Comprueba que en el fichero vuelve a aparecer `-----BEGIN PGP MESSAGE-----`.
5. Commit y push. No hay que tocar ningún secret.

En el log de cada envío aparece cuántas direcciones se han leído de cada grupo
(nunca las direcciones), para comprobar que el fichero se ha descifrado bien.
Si la frase de paso cambia, hay que actualizar el secret `GENTE_PASSPHRASE`.

El fichero no tiene extensión `.org` a propósito: los `.org` de `content/` se
exportan a la web, y este no debe publicarse.

Para probar el script en local sin el fichero cifrado se puede definir la
variable de entorno `EMAIL_RECIPIENTS` (lista separada por comas, sin grupos)
en lugar de `GENTE_PASSPHRASE`. No existe como secret en GitHub.

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
(contraseña de aplicación de 16 caracteres) y `GENTE_PASSPHRASE` (frase de
paso del fichero de participantes).

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
- `No se pudo descifrar la lista de participantes`: la frase de paso del
  secret `GENTE_PASSPHRASE` no coincide con la del fichero, o el fichero se
  guardó sin cifrar (comprueba que contiene `-----BEGIN PGP MESSAGE-----`).
- **El cron no se ejecuta.** Comprueba en Actions que "Send Email
  Notification" no está desactivado (ver *Keepalive*).
- **Límites de Gmail:** 500 correos al día y 100 destinatarios por mensaje (el
  script parte la lista en bloques de 80 si hiciera falta).

---

## 7. Pendiente y comprobaciones (29/09/2026)

Comprobaciones que solo pueden hacerse cuando ocurran:

- [ ] **Primera ejecución del cron** con el sistema nuevo (30/09/2026 por la
  mañana): el run de "Send Email Notification" debe salir en verde con
  "No hay sesión mañana" en el log. El paso de keepalive solo hace algo cuando
  el repositorio lleva 50 días sin commits.
- [ ] **Primera sesión real del curso**: al añadirla a `sesiones.org` y hacer
  push, el run de "Push Web Deploy" debe enviar el aviso a todos los
  participantes. Mirar el log del paso "Enviar aviso de sesiones nuevas". Ese
  camino se ha probado en simulación local, pero no con un envío real.
- [ ] **Primer recordatorio automático** la víspera de esa sesión.

Mejoras pendientes, no urgentes:

- [ ] **Instalación de Emacs en cada publicación.** El workflow instala Emacs
  con apt en cada push (varios minutos). Se puede cachear o usar una acción
  que lo instale más rápido.
- [ ] **Formulario sin etiquetas.** Sustituir las etiquetas `prueba`/`enviar`
  por un desplegable "Acción" dentro del formulario. Descartado el 29/09/2026
  por innecesario; se anota por si cambia de opinión.
- [ ] **Mensajes confidenciales.** Si hiciera falta enviar mensajes que no
  deban ser públicos, la solución estructural es mover el envío por issues a
  un repositorio privado de la organización (los issues de un repositorio
  privado solo los ven sus miembros). El workflow de ese repositorio leería
  `sesiones.org` y la lista de participantes de este.
