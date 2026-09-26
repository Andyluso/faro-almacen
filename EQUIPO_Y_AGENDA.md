# FARO: equipo, horarios y agenda

## Acceso
Abre la página habitual. El formulario de FARO reemplaza el cuadro de autenticación del navegador. La cuenta administradora inicial conserva el usuario y contraseña configurados antes de esta actualización. No hay registro público.

En «Equipo y accesos», crea una invitación, vincula el colaborador existente cuando corresponda y copia el enlace privado para entregárselo a esa persona. El enlace permite establecer una contraseña, funciona una sola vez y caduca a los tres días. No se envían correos automáticamente. Para recuperar acceso, un administrador o encargado autorizado genera un nuevo enlace desde la misma pantalla. Cada persona puede cambiar su contraseña desde su sesión.

| Cargo | Permisos |
| --- | --- |
| Administrador | Inventario, cuentas de todos los cargos, agenda, horarios y respaldos |
| Encargada | Inventario, agenda, horarios, decisiones de peticiones y cuentas de empleados |
| Empleado / asesor | Horarios publicados, sus peticiones y recordatorios dirigidos a su cuenta o a todo el equipo |

Solo la encargada aprueba, rechaza o revoca peticiones. El administrador puede consultarlas y planificar, pero no decidirlas. Los empleados actualizan su avance, pasos y observaciones; no crean ni eliminan tareas ni editan horarios. Los permisos se comprueban en el servidor, incluso al acceder directamente a una dirección.

## Horarios
Elige la semana, copia la anterior o solicita una sugerencia. Toca un turno para editarlo. Las peticiones aparecen en los días correspondientes y distinguen preferencias de restricciones y decisiones pendientes de aprobadas. Guardar conserva un borrador privado para gestión. «Revisar y publicar» muestra horas, cobertura, descansos, compensatorios y peticiones: requiere confirmación explícita antes de hacerlo visible al equipo. Las restricciones aprobadas incompatibles bloquean la publicación. La sugerencia nunca decide peticiones.

Los controles siguen la configuración de esta tienda: 42 horas ordinarias semanales, turno regular de 7 horas, reducción de 6, sábado de 8, domingo de 7 ordinarias más 1 extra y pausa de almuerzo separada. Son reglas configuradas de planificación. Revisa los avisos y las circunstancias reales antes de publicar. El historial permite recuperar un borrador anterior para revisarlo y volver a publicar.

## Agenda independiente
Crea una tarea con pasos para completar o un aviso con confirmación de lectura. Elige destinatarios: todo el equipo, personas concretas o tú mismo. Una tarea puede completarse por una sola persona o por cada destinatario. Cada persona registra pendiente, haciendo, con dificultad o finalizado, con observaciones. Para terminar una tarea con pasos, hay que marcarlos todos.

Las repeticiones diarias y semanales tienen avances independientes por fecha. «Posponer esta vez» cambia solo una ocurrencia. La gestión puede editar, adjuntar una foto, consultar el historial y eliminar con opción inmediata de deshacer. Los avisos registran la lectura de cada persona. La agenda funciona dentro de FARO; no envía notificaciones externas.

## Datos y mantenimiento
La actualización añade tablas al archivo existente del volumen; conserva inventario, fotos, Excel, colaboradores y datos previos. La agenda antigua se importa una sola vez; los horarios existentes quedan como borradores hasta publicación explícita. Las cuentas, agenda nueva, peticiones e historial se incluyen en los respaldos privados junto con los módulos anteriores. Los archivos de prueba locales no forman parte del despliegue.

Mantén una sola instancia escritora y el volumen persistente de Railway. Los respaldos contienen información privada, hashes de contraseñas y sesiones; no deben publicarse ni adjuntarse a GitHub. Una restauración debe invalidar las sesiones e invitaciones recuperadas antes de volver a abrir el servicio.

## Uso en teléfono y avisos de peticiones
El botón de menú abre las secciones en un panel lateral. La campana muestra el número de peticiones pendientes de decisión de todas las semanas; consultar un aviso no lo aprueba ni lo marca como resuelto. La bandeja distingue pendientes, aprobadas e historial y ofrece un acceso a la fecha solicitada. En horarios, el resumen muestra solo la semana elegida y cada turno distingue peticiones pendientes y aprobadas. Los avisos se actualizan al volver a FARO y cada minuto mientras la página está visible; no son notificaciones externas del teléfono.
