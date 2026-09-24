# FARO: correcciones y uso

## Cambios verificados
- Acceso con usuario y contraseña a la aplicación, datos, fotos y exportaciones.
- Los títulos de tareas, nombres y otros textos se muestran como texto, sin ejecutar HTML.
- Una sola ruta de estado, con consulta real de conectividad y estado de respaldo.
- Respaldos locales ZIP de la base completa (siete módulos) y archivos de uploads, cada 30 segundos cuando hay cambios; conserva los 20 más recientes.
- Botón «Descargar respaldo completo». Las credenciales no se incluyen en esos ZIP.
- Registro transaccional de cambios pendientes; una caída de red no los descarta.
- Copia privada en Supabase preparada, DESACTIVADA por defecto. No modifica las tablas antiguas: guarda ZIP recuperables con todos los módulos y archivos locales.
- El arranque no reemplaza datos locales por versiones de la nube.
- Se eliminó la ruta de estado duplicada y los turnos ficticios del panel.
- La eliminación de empleados elimina sus turnos relacionados. Los archivos desvinculados se conservan para recuperación.
- Los Excel vacíos y las imágenes inválidas se rechazan sin simular un guardado correcto.
- El navegador no almacena respuestas privadas en el service worker.

## Entrar
Abre iniciar_sistema.bat. Usa las credenciales entregadas en el archivo «Acceso FARO.txt».
Para cambiarlas, ejecuta `python configurar_acceso.py` dentro de esta carpeta.
En el celular utiliza HTTPS (el túnel existente); no compartas la contraseña por el enlace.

## Configurar el respaldo privado en una instalación nueva
1. Conserva una copia descargada con «Descargar respaldo completo» fuera del computador.
2. En el panel de TU proyecto Supabase, obtén una clave secreta de servidor y configúrala localmente como SUPABASE_SERVICE_ROLE_KEY. No la pegues en chats ni en JavaScript.
3. Ejecuta supabase_setup_fix.sql desde el SQL Editor como administrador. Cierra acceso anónimo a las tablas antiguas, hace privado garment-photos y crea faro-backups como privado. Revisa que no existan políticas adicionales propias que den acceso a esos buckets.
4. Configura FARO_PRIVATE_CLOUD_READY=1 y reinicia FARO.
5. Comprueba que el indicador muestre respaldo al día y que exista un ZIP en el bucket privado faro-backups. Descarga y prueba periódicamente una copia.

La copia se reintenta si falla y solo elimina pendientes que ya estaban en el ZIP enviado. Cambios hechos durante el envío permanecen pendientes. Los ZIP remotos se conservan; controla espacio y retención desde Supabase.
Los siete módulos se respaldan juntos. No es sincronización entre varios servidores: utiliza un solo servidor FARO como origen.
Fotos externas enlazadas en la base permanecen en Supabase; el ZIP incluye archivos presentes en uploads y sus referencias. Para una recuperación sin acceso a Supabase, conserva también una copia del bucket garment-photos.

## Restaurar
Detén FARO y conserva una copia de la carpeta actual. Abre un ZIP de respaldo y copia su carpeta backend sobre la del proyecto (inventario.db y uploads). Conserva la configuración de acceso y .env actuales. Reinicia FARO y verifica auditorías, colaboradores, horarios y tareas. No restaures sobre un servidor en uso.

## Verificación realizada
34 pruebas de la aplicación aprobadas, más pruebas de JavaScript para la inyección HTML y los argumentos de botones. Se probaron carga, validación y exportación de Excel, autenticación, bloqueos por origen, límite de intentos, respaldo/recuperación, integridad y rechazo de respaldo a un bucket público.
También se verificó una restauración real desde el bucket privado, la lectura autenticada de fotos y la subida y descarga de respaldos con comprobación SHA-256. Las tablas y los buckets privados requieren la clave de servidor.

## Diseño y despliegue en Railway
El panel organiza inventario prioritario, tareas, búsqueda y equipo del día con una paleta oliva y marfil. La navegación se adapta a escritorio y celular.
Conserva el volumen existente en `/app/backend/uploads`. Configura `FARO_UPLOADS_DIR=/app/backend/uploads` y `FARO_DATA_DIR=/app/backend/uploads/.faro`; los datos y los últimos 20 respaldos locales quedan en el volumen. La carpeta privada nunca se sirve por la ruta de archivos.
Para migrar un servidor existente, prepara un ZIP privado con su base de datos actual y archivos. Configura `FARO_REQUIRE_BOOTSTRAP=1`, `FARO_BOOTSTRAP_ARCHIVE` y `FARO_BOOTSTRAP_SHA256`, además del usuario, contraseña y clave privada. Si falta la base en el volumen, el arranque descarga el ZIP, valida su huella e integridad y lo restaura una sola vez. Si falla, el servicio no inicia con una base vacía. Los arranques posteriores conservan los cambios del volumen y los archivos existentes nunca son reemplazados por el respaldo inicial.
Para recuperar una copia más reciente tras perder el volumen, actualiza el nombre y SHA-256 del respaldo antes de reiniciar. Mantén una sola réplica con acceso de escritura a SQLite. Las dependencias de producción están fijadas en `requirements.lock`.
