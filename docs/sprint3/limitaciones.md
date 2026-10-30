# Sprint 3: limitaciones conocidas de la aplicación (se irán completando)

Fecha: 2026-10-28. Estado: borrador, tras el bloque B (tarea 3.3).

## Seguridad

1. **Sin detección de vida.** La app no distingue a una persona real de una foto, una pantalla o un video del usuario.
   No ofrece protección contra la suplantación. Se indica en la pantalla "Acerca de / limitaciones" y en el pie de todas las páginas.
2. **Cualquiera puede bloquear temporalmente a un usuario.** El usuario elige quién dice ser sin otra credencial. Por eso cualquier
   persona puede elegir el nombre de otro y fallar 3 veces seguidas (intentos denegados) para bloquearlo durante el tiempo configurado
   (60 s por defecto). Es una denegación de servicio temporal. Mitigaciones actuales:
   - el bloqueo es temporal;
   - el administrador puede desbloquear desde el panel;
   - cada intento queda registrado con fecha y usuario solicitado.

   No se resuelve en este prototipo.
3. **El tope general de intentos** (10 en 5 minutos por usuario, con pausa de 30 s) limita la carga. También puede afectar a un usuario
   legítimo si otra persona agota su tope.
4. **Contraseña de administrador única**, leída de la variable de entorno `FACEID_ADMIN_PASSWORD`. Tiene una pausa de 1 s tras cada
   contraseña incorrecta, pero no bloquea por intentos. La sesión de administrador caduca al reiniciar el servidor.
5. La app usa el servidor de desarrollo de Flask y escucha solo en `127.0.0.1`. No está pensada para una red ni para producción.

## Reconocimiento

6. El modelo y el umbral (0,5514) vienen del Sprint 2 y no se ajustaron para la cámara web. En esa evaluación las fotos eran de prensa
   y de personas famosas (ver `docs/sprint2/06_evaluacion_prueba.md`). Con usuarios desconocidos y cámara web puede rendir peor.
7. Los criterios de "no se pudo verificar de forma confiable" se calibraron con recortes del dataset, no con la cámara real:
   - borroso: varianza del laplaciano < 10;
   - oscuro: media de gris < 40;
   - sobreexpuesto: media de gris > 225;
   - rostro de menos de 60 px;
   - varios rostros.

   Hay que revisarlos con los voluntarios.
8. Si aparece más de una persona con un rostro claro y grande, el intento es "no concluyente". Las caras pequeñas del fondo se ignoran.

## Privacidad

9. Las plantillas y el registro de intentos se guardan en la carpeta privada `FACEID_APP_DATA` (por defecto `%USERPROFILE%\FaceID_privado`, fuera del repositorio), con permisos solo para
   el usuario de Windows que ejecuta la app (`icacls`).
   - **No están cifrados.**
   - El registro de intentos guarda el seudónimo solicitado, la fecha y el resultado.
   - Al eliminar un usuario se borran su plantilla, sus metadatos, sus fotos (si se conservaron), su estado de intentos y sus filas del registro.
   - El registro de acciones del administrador (`registro_admin.csv`) conserva la fecha y la acción.

## Exposición por túnel (Cloudflare Tunnel)

10. Con el túnel, las imágenes viajan cifradas (HTTPS) hasta Cloudflare, que termina el cifrado y las reenvía a la laptop. La app no
    las guarda, pero **pasan por la infraestructura de un tercero**. El túnel rápido (`trycloudflare.com`) es para pruebas, no tiene
    garantías de servicio y su dirección cambia en cada reinicio.
11. Cualquiera con el enlace y la contraseña de acceso público puede intentar verificarse. Mitigaciones:
    - autenticación básica (con 10 contraseñas fallidas por IP en 10 minutos, esa IP espera);
    - 20 verificaciones por minuto por IP real;
    - el tope por usuario y el bloqueo.
12. La separación entre la instancia pública y la de administración depende de que el túnel apunte **solo** al puerto 5000. Por el túnel
    todas las peticiones llegan desde 127.0.0.1, así que la app no puede distinguirlas por IP local. El script fija el destino del túnel.
13. Los límites por IP se guardan en memoria: se reinician al reiniciar la instancia pública.

## Modos de ingreso (Nombre + rostro, Solo cámara, palabra clave)

14. **El modo "Solo cámara" (identificación 1:N) NO fue evaluado en el Sprint 2.** En el Sprint 2 solo se evaluó la verificación 1 a 1
    (FAR 0,041 % y FRR 1,00 % con fotos de Kaggle). En 1:N el rostro se compara con todos los usuarios registrados en la app, así que
    **el riesgo de aceptar a otra persona crece con el número de usuarios**: con N usuarios, un impostor tiene N oportunidades de parecerse
    a alguien.
15. El margen sobre el segundo candidato (`MARGEN_1N` = 0,05) es un valor inicial **no calibrado**. Con un solo usuario registrado el margen
    no actúa y el modo B equivale a verificar contra esa única plantilla.
16. El modo B no compara con las 24 identidades del dataset, solo con los usuarios registrados en la app.
17. **La palabra clave añade un segundo factor**, pero su seguridad depende de que sea difícil de adivinar:
    - se guarda solo como hash scrypt con sal;
    - se compara con `hmac.compare_digest`;
    - tres claves incorrectas bloquean al usuario.

    El administrador la escribe en un cuadro de diálogo del navegador que no la oculta: no debe hacerlo con alguien mirando la pantalla.
18. **Bloqueo por IP del modo B:**
    - en local todas las peticiones vienen de 127.0.0.1, así que el bloqueo afecta a todos los que usan el modo B en ese equipo;
    - por el túnel se usa la IP real (`CF-Connecting-IP`);
    - la IP se guarda como hash con sal local, no en claro;
    - cualquiera puede bloquear temporalmente el modo B de su red fallando 3 veces.
19. El paso de la palabra clave caduca a los 120 s y está ligado a la IP del paso del rostro. Si se reinicia la instancia entre los dos
    pasos, hay que empezar de nuevo.

## Administración remota por Tailscale

24. Con `tailscale serve`, **cualquier dispositivo de la tailnet** llega a la página de inicio de sesión del administrador (y a la página
    principal con el modo explicación). La única barrera dentro de la tailnet es la contraseña de administrador. Por eso la cuenta de
    Tailscale debe tener verificación en dos pasos y no se deben compartir dispositivos ni invitar a otras personas a esa tailnet.
25. El límite de contraseñas de administrador fallidas es global (por el proxy todo llega desde 127.0.0.1): alguien dentro de la tailnet
    puede bloquear el inicio de sesión del administrador 10 minutos.
26. `tailscale funnel` publicaría el panel en internet. La app rechaza las peticiones con la cabecera `Tailscale-Funnel-Request`, pero
    esa defensa depende de que Tailscale la añada; la protección real es no usar Funnel y revisar `tailscale serve status`.
27. Un teléfono perdido con Tailscale abierto sigue dentro de la tailnet hasta que se elimina en la consola de Tailscale.

## Modo explicación («¿Cómo decidió la máquina?»)

20. **Muestra puntuaciones, el umbral y, en «Solo cámara», los seudónimos de los 3 candidatos más parecidos.** Por eso solo existe en
    la instancia local (la pública del túnel nunca lo ofrece) y se apaga con `FACEID_EXPLICACION=0`. Es una herramienta para la
    exposición en clase, no para usuarios finales: con las puntuaciones a la vista, un atacante podría ajustar una foto hasta pasar el umbral.
21. Con palabra clave, la explicación se entrega **después** del paso 2, para no revelar en el paso 1 si el rostro coincidió.
22. Los mosaicos muestran 8 de los cientos de mapas de activación de cada capa (los de mayor activación media). El mapa «dónde se activa
    la red» es la activación media de los bloques Inception-ResNet A superpuesta al rostro: **no es Grad-CAM** ni una explicación causal
    de la decisión.
23. Las capas se recorren con el mismo modelo, sin modificarlo; una prueba comprueba que el vector obtenido capa por capa coincide con
    el de la red completa. Los fotogramas que se dibujan en el panel solo existen en la memoria del navegador; el servidor no guarda nada.
