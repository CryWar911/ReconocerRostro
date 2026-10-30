# Medir el tiempo de punta a punta desde un teléfono por el túnel

Objetivo: medir el tiempo real de una verificación hecha desde un teléfono, separando la **captura** en el teléfono
(unos 1,6–2 s), el **envío y procesamiento** (red del túnel más servidor) y el tiempo del **servidor**, y compararlo con el
objetivo de 3 s (RNF02). Estas mediciones las hace el equipo; hasta entonces el resumen del Sprint 3 las marca como pendientes.

## Preparación (en la laptop)

1. Instalar `cloudflared` una sola vez: `winget install --id Cloudflare.cloudflared`.
2. Desactivar la suspensión y conectar el cargador. El script mantiene el equipo despierto mientras está abierto.
3. Arrancar con el modo pruebas (PowerShell, en `D:\IA\FaceID`):
   ```
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_tunel.ps1 -ModoPruebas
   ```
   - El script pide dos contraseñas distintas: la de **acceso público** (para el teléfono) y la del **administrador** (solo en la laptop).
   - Al final muestra la dirección `https://….trycloudflare.com`.
4. En la laptop, abrir `http://127.0.0.1:5001/admin/` y comprobar que el voluntario de la prueba está registrado.

## En el teléfono

1. Conectarlo a una red distinta de la de la laptop, por ejemplo datos móviles, para medir la ruta real por internet. Anotar el tipo de red.
2. Abrir la dirección `https://….trycloudflare.com` en Chrome (Android) o Safari (iPhone). Al pedir usuario y contraseña, el usuario
   puede ser cualquiera y la contraseña es la de acceso público.
3. En "Caso de prueba", escribir un ID de medición, por ejemplo `TEL01` para datos móviles o `TEL02` para wifi.
4. Elegir el seudónimo del voluntario, pulsar *Encender cámara* (aceptar el permiso; se usa la cámara frontal) y luego *Verificar*.
5. Repetir **10 veces** en luz normal.
   - El límite es de 20 verificaciones por minuto por IP y de 10 intentos en 5 minutos por usuario. Si aparece "Demasiados intentos",
     esperar los segundos indicados.
   - Debajo del resultado, la pantalla muestra: `Tiempo total X s (captura A s + envío y procesamiento B s; servidor C s)`.

## Resumen (en la laptop, al terminar)

Cerrar el script con Enter y ejecutar:

```
.venv/Scripts/python -m app.resumen_pruebas --csv docs/sprint3/resumen_tiempos_telefono.csv
```

Para cada caso (`TEL01`, `TEL02`…) da la mediana y el p95 de:
- `segundos_captura`: la ráfaga en el teléfono;
- `segundos_servidor`: el procesamiento en la laptop;
- `segundos_peticion`: la petición en el servidor;
- `segundos_total_cliente`: lo que espera el usuario, medido en el teléfono, incluida la red del túnel.

La diferencia entre el total y la suma de captura y petición es, aproximadamente, la red: subida de los 5 JPEG y bajada de la respuesta.

**Anotar con el resultado:** fecha, modelo de teléfono, navegador y versión, tipo de red, y si la laptop usaba GPU o CPU. No anotar
nombres; usar seudónimos. El resumen no contiene imágenes ni seudónimos.

## Observaciones

- Con el túnel, las imágenes viajan cifradas (HTTPS) hasta Cloudflare, que las reenvía a la laptop. La app no las guarda, pero pasan por
  la infraestructura de un tercero. Anotarlo en el informe.
- La dirección `trycloudflare.com` cambia cada vez que se reinicia el túnel.
