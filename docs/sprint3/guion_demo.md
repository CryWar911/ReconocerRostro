# Guion de la demostración en clase (Sprint 3)

Duración orientativa: 10 a 12 minutos. Todo corre en una sola laptop, sin internet. La app escucha solo en `127.0.0.1`.

## Lista de comprobación previa (el día anterior y 15 minutos antes)

| ✔ | Qué comprobar | Cómo |
|---|---|---|
| ☐ | Entorno y modelo | `.venv/Scripts/python -m pytest app/tests -q` termina sin fallos. Incluye la prueba de integridad del modelo: hash y umbral 0,5514. |
| ☐ | Cámara | Abrir la app en Chrome o Edge, pulsar *Encender cámara* y aceptar el permiso. Si otra app (Zoom, Teams) usa la cámara, cerrarla. |
| ☐ | Luz | Luz frontal o lateral suave sobre la cara; nada de ventana detrás de la persona. Probar un intento de CF01 antes de empezar. |
| ☐ | Usuarios para los tres modos | Al menos 2 voluntarios registrados (para que el modo «Solo cámara» tenga que elegir) y uno de ellos con «Rostro + palabra clave». La palabra clave la conoce solo ese voluntario. |
| ☐ | Plantillas cargadas | En *Administración*, los voluntarios aparecen con su seudónimo y "Firmada (fecha)". En *Iniciar sesión*, el grupo "Usuarios registrados (demostración)" los muestra. |
| ☐ | Contraseña de administrador | Definida en `FACEID_ADMIN_PASSWORD` en la terminal que arranca la app. La conoce quien presenta y no se proyecta. |
| ☐ | Carpeta de datos | `FACEID_APP_DATA` apunta a la carpeta privada correcta (por defecto `%USERPROFILE%\FaceID_privado`). `git status` no muestra datos. |
| ☐ | Bloqueos limpios | En el panel no hay usuarios bloqueados. Si los hay, *Desbloquear*. |
| ☐ | Copia de respaldo | Copia de la carpeta privada (solo plantillas y metadatos) en una memoria USB cifrada o una carpeta privada; nunca en git ni en un servicio público. |
| ☐ | Material del paso 1 | Resultados agregados de la prueba con el video (tarea 2.6), o el aviso de que está pendiente. |
| ☐ | Plan B | Los videos del ensayo o capturas de pantalla de un intento permitido y uno denegado, por si falla la cámara. |
| ☐ | Pantalla | Proyectar el navegador. La terminal con la contraseña no debe verse. Volumen y notificaciones desactivados. |
| ☐ | Energía | **Suspensión del equipo desactivada** (Configuración > Sistema > Inicio/apagado y suspensión: "Nunca" con el cargador) y **cargador conectado**. El script del túnel además mantiene el equipo despierto mientras está abierto. |
| ☐ | Túnel (si se usan teléfonos) | `cloudflared` instalado; el script `iniciar_demo_tunel.ps1` muestra la dirección `https://….trycloudflare.com`. **Si se reinicia el túnel, la dirección cambia**: volver a compartirla. |
| ☐ | Dos contraseñas distintas | Acceso público (la reciben los teléfonos) y administrador (nunca se comparte; la administración solo se abre en `http://127.0.0.1:5001`). |
| ☐ | Prueba desde un teléfono | Antes de la clase, abrir la dirección pública con datos móviles, aceptar el permiso de cámara y hacer un intento. |

Arranque (PowerShell, desde `D:\IA\FaceID`). Hay dos opciones:

**A. Solo en la laptop** (la demo se hace con la cámara de la laptop):

```
$env:FACEID_ADMIN_PASSWORD = "<contraseña>"
.venv/Scripts/python -m app
```

**B. Con teléfonos por túnel.** Instancia pública (5000) por el túnel y administración (5001) solo local:

```
powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_tunel.ps1
```

En la opción B:
- los voluntarios usan la dirección pública en su teléfono, con la contraseña de acceso público;
- quien presenta usa `http://127.0.0.1:5001/admin/` en la laptop para el panel (registrar, ver bloqueos, desbloquear);
- la pública ve los cambios sin reiniciar;
- la página pública muestra el aviso de demostración sin detección de vida, y que las imágenes no se guardan.

## Desarrollo de la demostración

1. **Video de los voluntarios y prueba del modelo (tarea 2.6, script aparte).**
   - Mostrar el resumen agregado de `src.video_verificacion` (FAR y FRR por fotograma y por ventana, fotogramas sin rostro, tiempos).
   - Explicar que usa el mismo modelo, el mismo umbral (0,5514) y la misma votación (3 de 5) que la app.
   - Si aún no se ha hecho, decirlo tal cual: "pendiente".
2. **Abrir la web local** en `http://127.0.0.1:5001` (opción A). Comentar que funciona solo en esta máquina y que las imágenes no se guardan.
3. **Voluntario registrado aceptado.**
   - El voluntario elige su seudónimo, enciende la cámara y pulsa *Verificar*.
   - Resultado esperado: **Acceso permitido**. Señalar los 5 fotogramas válidos y el tiempo total, separado en captura y procesamiento.
   - **Cómo decide la máquina:** activar el interruptor «Mostrar cómo decide la máquina» y repetir el intento. Recorrer los 6 pasos
     del panel: detección (cajas), recorte 160 × 160, capas de la CNN (de bordes a rasgos abstractos), vector de 512, barras de similitud
     contra el umbral 0,5514 y votación 3 de 5. Aclarar que este panel muestra puntuaciones y por eso solo existe en la versión local.
3 bis. **Solo cámara (1:N).**
   - En la pestaña **Solo cámara**, el mismo voluntario pulsa *Identificarme* sin elegir su nombre.
   - Resultado esperado: **Acceso permitido** y «Hola, <seudónimo>».
   - Explicar que este modo **no se evaluó en el Sprint 2** y que el riesgo crece con el número de usuarios.
   - Con el modo explicación activo, mostrar en el paso 5 los candidatos de cada fotograma y por qué gana uno (umbral y margen 0,05).
3 ter. **Rostro + palabra clave.**
   - El voluntario con clave verifica su rostro (en cualquiera de los dos modos); la app pide la palabra clave y, al escribirla, lo deja pasar.
   - Si la escribe mal, el mensaje es «Acceso denegado», sin decir si falló el rostro o la clave.
4. **Impostor denegado.**
   - Un no registrado, o un voluntario que elige el seudónimo de otro, intenta entrar.
   - Resultado esperado: **Acceso denegado**.
5. **No concluyente y bloqueo.**
   - Tapar la cámara y verificar: "No se pudo verificar de forma confiable", con el motivo "no se detectó ningún rostro". Aclarar que esto **no** cuenta para el bloqueo.
   - En «Solo cámara», una persona no registrada obtiene «No se pudo identificar de forma confiable». Tras 3 intentos seguidos se bloquea ese equipo 60 s; en local es la propia laptop, así que conviene hacerlo al final.
   - **Bloqueo con un usuario de prueba, no con un voluntario real:** un voluntario elige la identidad del dataset **"Tom Cruise"** y pulsa *Verificar* 4 veces. Los intentos 1 a 3 salen denegados (el 3.º avisa del bloqueo) y el 4.º muestra "Usuario bloqueado temporalmente".
   - Abrir *Administración*: aparece el bloqueo y los intentos registrados (fecha, usuario y resultado, sin imágenes). Pulsar *Desbloquear*.
6. **Limitaciones.**
   - Abrir *Acerca de / limitaciones*.
   - **No hay detección de vida**: una foto o un video del usuario podría ser aceptado.
   - Las cifras del Sprint 2 son con fotos de Kaggle, no con cámara web.
   - Cualquiera puede bloquear temporalmente a un usuario eligiendo su nombre.
   - Es un prototipo académico, solo local.

## Qué hacer si algo falla

| Problema | Qué hacer |
|---|---|
| La cámara no enciende ("Permission denied" o pantalla negra) | Revisar el permiso de cámara del navegador (icono del candado); cerrar otras apps que usen la cámara; recargar la página. Si persiste, usar el Plan B y explicar el flujo con las capturas. |
| Siempre "No se pudo verificar" (oscura o sin rostro) | Acercarse, ponerse de frente y encender una luz frontal. Si el motivo es "borrosa", quedarse quieto y limpiar la lente. |
| Un voluntario registrado es denegado | Repetir con mejor luz y de frente. Si se repite, anotarlo como resultado real (no ocultarlo). Si queda bloqueado, *Desbloquear* desde el panel. |
| El voluntario quedó bloqueado por error | *Administración > Desbloquear*. |
| La app tarda mucho o no responde | Comprobar en la terminal que dice "Modelo cargado". Reiniciar con `Ctrl+C` y volver a arrancar; los bloqueos se conservan y las plantillas siguen en la carpeta privada. |
| No aparecen los voluntarios | Revisar que `FACEID_APP_DATA` apunta a la carpeta correcta antes de arrancar; si se perdió, restaurar la copia de respaldo. |
| La administración dice "deshabilitada" | La terminal no tiene `FACEID_ADMIN_PASSWORD`; definirla y reiniciar la app. |
| Falla la prueba de integridad del modelo | No hacer la demo con ese modelo: volver a copiar `models/verificador_facenet_vggface2/` original. |
| El teléfono no abre la dirección pública | El túnel se reinició y la dirección cambió: mirar la nueva en la ventana del script. Si el script se cerró, volver a ejecutarlo y compartir la nueva dirección. |
| El teléfono pide usuario y contraseña una y otra vez | La contraseña de acceso público es incorrecta (el usuario puede ser cualquiera). Tras 10 fallos, esa conexión espera unos minutos. |
| El teléfono no enciende la cámara | Aceptar el permiso de cámara del navegador; la dirección debe empezar por `https://` (la de trycloudflare lo hace). |
| "Demasiadas peticiones" en el teléfono | Límite de 20 verificaciones por minuto por conexión: esperar los segundos indicados. |
| La laptop se suspendió | Reactivarla y comprobar que el script sigue abierto. Si se cerró el túnel, volver a ejecutarlo: la dirección cambia. |

## Después de la demostración

- Si el consentimiento de los voluntarios era solo para la demo: *Eliminar* a cada voluntario desde el panel. Así se borran su plantilla, sus metadatos, sus fotos (si las hubiera) y sus intentos.
- Borrar la copia de respaldo si ya no hace falta.
- Para borrar todos los datos de la app y verificarlo: `powershell -ExecutionPolicy Bypass -File scriptsorrar_datos_app.ps1` (con las instancias cerradas).
- Cerrar el script del túnel (Enter): se cierran el túnel y las dos instancias, y la dirección pública deja de funcionar.
