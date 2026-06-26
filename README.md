# Gestor de Profesiones — Warhammer Fantasy Roleplay

Aplicación web para gestionar profesiones, habilidades, talentos y personajes del juego de rol **Warhammer Fantasy Roleplay (2ª edición)**. Permite importar profesiones desde PDFs del libro de reglas (incluyendo páginas escaneadas en inglés o español), buscar rutas de progresión entre profesiones y crear personajes.

---

## Tabla de contenidos

- [Características](#características)
- [Tecnologías](#tecnologías)
- [Instalación rápida con Docker](#instalación-rápida-con-docker)
- [Instalación local para desarrollo](#instalación-local-para-desarrollo)
- [Configuración](#configuración)
- [Comandos de administración y mantenimiento](#comandos-de-administración-y-mantenimiento)
- [Guía de operación — Administrador](#guía-de-operación--administrador)
- [Guía de operación — Usuario](#guía-de-operación--usuario)
- [Modelo de datos](#modelo-de-datos)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Características

| Módulo | Descripción |
|---|---|
| **Profesiones** | Catálogo con todos los campos WFRP2: perfil primario y secundario, habilidades con especializaciones y grupos de elección, talentos, enseres, accesos y salidas |
| **Importación PDF** | Sube un PDF del libro (escaneado o digital), con OCR automático y traducción inglés → español |
| **Buscador de caminos** | Encuentra hasta 5 rutas entre dos profesiones mostrando características acumuladas, habilidades y enseres necesarios en cada paso; todos los pasos de una ruta pueden verse simultáneamente |
| **Habilidades y Talentos** | Catálogo completo con buscador avanzado (nombre / todos los campos); importación y exportación en texto, CSV y Excel; filtros por tipo (Básica / Avanzada) y por característica asociada; cada entrada muestra qué profesiones la otorgan |
| **Personajes** | Crea personajes asignándoles una carrera profesional con múltiples profesiones en orden |
| **Sistema de permisos** | Control granular por función: plantillas de permisos reutilizables + asignaciones directas por usuario; los administradores tienen acceso total |

---

## Tecnologías

- **Backend:** Python 3.11 · Flask 3 · SQLAlchemy · Flask-Login
- **Base de datos:** MySQL 8
- **OCR:** Tesseract 5 (vía pytesseract) + pdf2image · PyMuPDF (PDFs digitales)
- **Traducción:** deep-translator (Google Translate) · langdetect
- **Pathfinding:** networkx (BFS)
- **Frontend:** Bootstrap 5 · Cinzel / Crimson Text (Google Fonts)
- **Importación/Exportación:** openpyxl (Excel), csv estándar, formato texto propio
- **Infraestructura:** Docker · Docker Compose · Gunicorn

---

## Instalación rápida con Docker

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose)
- Git

### Pasos

```bash
# 1. Clona el repositorio
git clone https://github.com/jmsanesteban/ProfesionesWH.git
cd ProfesionesWH

# 2. Copia y edita el fichero de entorno
cp .env.example .env
# Edita .env: cambia las contraseñas y la SECRET_KEY antes de usar en producción

# 3. Levanta la aplicación
docker-compose up --build
```

La primera vez tarda unos minutos mientras se construye la imagen y se descargan las dependencias del sistema (Tesseract, Poppler, etc.).

Una vez arrancado, abre **http://localhost:5000** en el navegador.

El usuario administrador se crea automáticamente con las credenciales definidas en `.env` (`ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`).

### Apagar y reiniciar

```bash
# Parar los contenedores (conserva los datos)
docker-compose down

# Volver a arrancar (sin reconstruir)
docker-compose up

# Parar y eliminar también los datos (base de datos)
docker-compose down -v
```

### Ver logs en tiempo real

```bash
docker-compose logs -f app
docker-compose logs -f db
```

---

## Instalación local para desarrollo

Para desarrollar sin Docker necesitas MySQL, Python 3.11+ y Tesseract instalados en tu máquina.

### 1. MySQL

Crea la base de datos y el usuario:

```sql
CREATE DATABASE profesiones_wh CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'whuser'@'localhost' IDENTIFIED BY 'whpassword';
GRANT ALL PRIVILEGES ON profesiones_wh.* TO 'whuser'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Tesseract OCR

**Windows:** Descarga el instalador desde [github.com/UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) e instala los paquetes de idioma `spa` y `eng`.

**Linux/macOS:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils  # Debian/Ubuntu
brew install tesseract tesseract-lang poppler  # macOS
```

### 3. Entorno Python

```bash
# Crea y activa el entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Instala dependencias
pip install -r requirements.txt
```

### 4. Configuración

```bash
cp .env.example .env
```

Edita `.env` y cambia `DATABASE_URL` para apuntar a localhost:

```
DATABASE_URL=mysql+pymysql://whuser:whpassword@localhost:3306/profesiones_wh
FLASK_ENV=development
```

### 5. Migraciones y arranque

```bash
# Inicializa las tablas y siembra datos iniciales (permisos, plantillas, sinónimos)
flask init-db

# Crea el usuario administrador
flask create-admin

# Arranca el servidor de desarrollo
flask run
```

La app estará en **http://localhost:5000**.

---

## Configuración

Todas las variables se definen en el fichero `.env` (copia de `.env.example`):

| Variable | Descripción | Por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Flask (CSRF, sesiones). **Cambia en producción.** | `change-this-...` |
| `FLASK_ENV` | `development` activa el modo debug. En producción usa `production`. | `development` |
| `MYSQL_DATABASE` | Nombre de la base de datos | `profesiones_wh` |
| `MYSQL_USER` | Usuario de MySQL | `whuser` |
| `MYSQL_PASSWORD` | Contraseña del usuario MySQL | `whpassword` |
| `MYSQL_ROOT_PASSWORD` | Contraseña root de MySQL (solo Docker) | `rootpassword` |
| `DATABASE_URL` | URL de conexión completa usada por Flask | `mysql+pymysql://...` |
| `ADMIN_USERNAME` | Nombre del usuario administrador inicial | `admin` |
| `ADMIN_EMAIL` | Email del administrador inicial | `admin@example.com` |
| `ADMIN_PASSWORD` | Contraseña del administrador inicial | `changeme123` |
| `UPLOAD_FOLDER` | Ruta donde se guardan PDFs e imágenes subidas | `/app/uploads` |
| `MAX_CONTENT_LENGTH` | Tamaño máximo de fichero en bytes | `52428800` (50 MB) |

> **Importante:** En producción genera una `SECRET_KEY` larga y aleatoria:
> ```python
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## Comandos de administración y mantenimiento

Los comandos de Docker funcionan igual en Windows y Linux. En Windows se ejecutan en **PowerShell** (o CMD); en Linux/macOS en cualquier terminal. Las únicas diferencias son las rutas de fichero y algunos comandos de utilidad del sistema operativo.

> Los nombres de los contenedores son `profesiones_wh_app` (aplicación) y `profesiones_wh_db` (MySQL). Si los cambiaste en `docker-compose.yml`, ajusta los comandos en consecuencia.

---

### Ciclo de vida de los contenedores

| Acción | Comando |
|---|---|
| Arrancar (sin reconstruir) | `docker-compose up -d` |
| Arrancar con reconstrucción de imagen | `docker-compose up --build -d` |
| Parar (sin borrar datos) | `docker-compose down` |
| Parar y borrar volúmenes (⚠️ borra la BD) | `docker-compose down -v` |
| Reiniciar solo la app | `docker-compose restart app` |
| Reconstruir y reiniciar solo la app | `docker-compose up --build -d app` |
| Ver estado de los contenedores | `docker-compose ps` |

---

### Logs

#### Windows — PowerShell

```powershell
# Logs en tiempo real de toda la pila
docker-compose logs -f

# Solo la aplicación
docker-compose logs -f app

# Solo la base de datos
docker-compose logs -f db

# Últimas 100 líneas de la aplicación
docker-compose logs --tail=100 app

# Buscar errores en los logs de la app (requiere Select-String)
docker-compose logs app 2>&1 | Select-String "ERROR", "Exception", "Traceback"
```

#### Linux / macOS

```bash
# Logs en tiempo real de toda la pila
docker-compose logs -f

# Solo la aplicación
docker-compose logs -f app

# Solo la base de datos
docker-compose logs -f db

# Últimas 100 líneas de la aplicación
docker-compose logs --tail=100 app

# Buscar errores en los logs de la app
docker-compose logs app 2>&1 | grep -E "ERROR|Exception|Traceback"
```

---

### Comandos Flask (init, admin, shell)

Todos se ejecutan dentro del contenedor de la app con `docker exec`.

#### Windows — PowerShell

```powershell
# Crear / migrar tablas de base de datos (ejecutar tras cada actualización del código)
# También siembra permisos, plantillas y sinónimos por defecto (idempotente)
docker exec profesiones_wh_app flask init-db

# Crear el usuario administrador (usa las variables ADMIN_* del .env)
docker exec profesiones_wh_app flask create-admin

# Abrir una shell interactiva de Python con el contexto de la app
docker exec -it profesiones_wh_app flask shell

# Abrir una shell Bash dentro del contenedor
docker exec -it profesiones_wh_app bash
```

#### Linux / macOS

```bash
# Crear / migrar tablas de base de datos
docker exec profesiones_wh_app flask init-db

# Crear el usuario administrador
docker exec profesiones_wh_app flask create-admin

# Shell interactiva de Python con contexto de la app
docker exec -it profesiones_wh_app flask shell

# Shell Bash dentro del contenedor
docker exec -it profesiones_wh_app bash
```

---

### Acceso a la base de datos MySQL

#### Windows — PowerShell

```powershell
# Abrir el cliente MySQL interactivo en el contenedor de BD
# (te pedirá la contraseña definida en .env → MYSQL_PASSWORD)
docker exec -it profesiones_wh_db mysql -u whuser -p profesiones_wh

# Con contraseña directa (sin prompt; sustituye 'whpassword' por la real)
docker exec -it profesiones_wh_db mysql -u whuser -pwhpassword profesiones_wh

# Ejecutar una consulta SQL de una sola línea
docker exec profesiones_wh_db mysql -u whuser -pwhpassword profesiones_wh -e "SELECT COUNT(*) FROM professions;"
```

#### Linux / macOS

```bash
# Abrir el cliente MySQL interactivo
docker exec -it profesiones_wh_db mysql -u whuser -p profesiones_wh

# Ejecutar una consulta SQL de una sola línea
docker exec profesiones_wh_db mysql -u whuser -pwhpassword profesiones_wh -e "SELECT COUNT(*) FROM professions;"
```

---

### Copias de seguridad de la base de datos

#### Windows — PowerShell

```powershell
# Exportar la BD completa a un fichero SQL con fecha en el nombre
$fecha = Get-Date -Format "yyyyMMdd_HHmm"
docker exec profesiones_wh_db mysqldump -u whuser -pwhpassword profesiones_wh | Out-File -Encoding utf8 "backup_$fecha.sql"

# Restaurar desde un fichero SQL
Get-Content "backup_20240101_1200.sql" | docker exec -i profesiones_wh_db mysql -u whuser -pwhpassword profesiones_wh
```

#### Linux / macOS

```bash
# Exportar la BD completa a un fichero SQL con fecha en el nombre
docker exec profesiones_wh_db mysqldump -u whuser -pwhpassword profesiones_wh > "backup_$(date +%Y%m%d_%H%M).sql"

# Restaurar desde un fichero SQL
docker exec -i profesiones_wh_db mysql -u whuser -pwhpassword profesiones_wh < backup_20240101_1200.sql
```

---

### Gestión de ficheros subidos (PDFs e imágenes)

Los uploads se almacenan en el volumen Docker `uploads`. Para acceder a ellos:

#### Windows — PowerShell

```powershell
# Copiar todos los uploads a una carpeta local
docker cp profesiones_wh_app:/app/uploads ./uploads_backup

# Copiar una carpeta local de vuelta al contenedor
docker cp ./uploads_backup/. profesiones_wh_app:/app/uploads/

# Ver qué hay en la carpeta de uploads
docker exec profesiones_wh_app ls -lh /app/uploads/
```

#### Linux / macOS

```bash
# Copiar todos los uploads a una carpeta local
docker cp profesiones_wh_app:/app/uploads ./uploads_backup

# Copiar una carpeta local de vuelta al contenedor
docker cp ./uploads_backup/. profesiones_wh_app:/app/uploads/

# Ver qué hay en la carpeta de uploads
docker exec profesiones_wh_app ls -lh /app/uploads/
```

---

### Actualizar la aplicación (nueva versión del código)

#### Windows — PowerShell

```powershell
# 1. Obtener los cambios del repositorio
git pull

# 2. Reconstruir la imagen e iniciar
docker-compose up --build -d

# 3. Aplicar migraciones de base de datos si las hay
docker exec profesiones_wh_app flask init-db
```

#### Linux / macOS

```bash
# 1. Obtener los cambios del repositorio
git pull

# 2. Reconstruir la imagen e iniciar
docker-compose up --build -d

# 3. Aplicar migraciones de base de datos si las hay
docker exec profesiones_wh_app flask init-db
```

---

### Diagnóstico rápido

#### Windows — PowerShell

```powershell
# Estado general de los contenedores
docker-compose ps

# Uso de recursos (CPU, memoria, red) en tiempo real
docker stats profesiones_wh_app profesiones_wh_db

# Inspeccionar variables de entorno cargadas en el contenedor
docker exec profesiones_wh_app env | Select-String "FLASK|MYSQL|ADMIN"

# Ver el espacio ocupado por los volúmenes Docker
docker system df

# Limpiar imágenes y capas no utilizadas (libera espacio en disco)
docker image prune -f
```

#### Linux / macOS

```bash
# Estado general de los contenedores
docker-compose ps

# Uso de recursos en tiempo real
docker stats profesiones_wh_app profesiones_wh_db

# Inspeccionar variables de entorno cargadas en el contenedor
docker exec profesiones_wh_app env | grep -E "FLASK|MYSQL|ADMIN"

# Ver el espacio ocupado por los volúmenes Docker
docker system df

# Limpiar imágenes y capas no utilizadas
docker image prune -f
```

---

### Referencia rápida de comandos Flask CLI

| Comando | Descripción |
|---|---|
| `flask init-db` | Crea todas las tablas, aplica migraciones incrementales de columnas y siembra permisos, plantillas y sinónimos por defecto. Seguro de ejecutar múltiples veces. |
| `flask create-admin` | Crea el usuario administrador definido en las variables `ADMIN_*` del `.env`. Si ya existe, no hace nada. |
| `flask shell` | Abre una shell Python con la app cargada. Útil para consultas y depuración ad-hoc. |
| `flask db migrate` | (Modo desarrollo) Genera una migración Alembic a partir de los cambios en los modelos. |
| `flask db upgrade` | (Modo desarrollo) Aplica las migraciones Alembic pendientes. |

---

## Guía de operación — Administrador

### Acceso al panel de administración

Inicia sesión con las credenciales de administrador y accede desde el menú **Admin → Panel**.

---

### Importar profesiones desde un PDF

Esta es la forma principal de cargar datos masivos desde el libro de reglas.

> **Importante:** Antes de importar un PDF, asegúrate de tener el catálogo de habilidades y talentos cargado. El sistema valida automáticamente las habilidades y talentos extraídos contra la base de datos.

1. Ve a **Admin → Subir PDF**.
2. Selecciona el archivo PDF y pulsa **Procesar PDF**.
3. El sistema ejecuta la siguiente pipeline automáticamente:
   - Extrae el texto de cada página con **PyMuPDF** (PDFs digitales).
   - Si una página tiene poco texto (página escaneada), la convierte a imagen y ejecuta **OCR** con Tesseract.
   - Detecta el idioma; si es **inglés**, traduce al español automáticamente (nombre original preservado en el campo EN).
   - Corrige nombres con letras separadas por el OCR (p.ej. `A Nimal T Rainer` → `Animal Trainer`).
   - Analiza el texto buscando bloques de profesión (nombre en mayúsculas, tablas de perfil, secciones de habilidades, etc.).
4. Se muestra la pantalla de **revisión**: una tarjeta por cada profesión detectada, con los campos pre-rellenados y chips de colores para habilidades y talentos (verde = encontrado en BD, naranja = no encontrado).
5. Se muestran advertencias si la profesión no tiene salidas, no tiene entradas, o tiene habilidades/talentos sin correspondencia en la BD.
6. **Revisa y corrige** los datos de cada profesión. Presta especial atención a las características numéricas y los chips naranja.
7. Pulsa **Guardar esta profesión** en cada tarjeta que quieras importar.

> **Nota:** Las salidas y accesos entre profesiones se guardan como texto pendiente de vincular. Después de importar, edita cada profesión para asignar las salidas correctas desde el formulario.

---

### Gestionar profesiones manualmente

Ve a **Admin → Nueva Profesión** o al icono de edición de cualquier profesión existente.

#### Campos del formulario

**Información básica**
- **Nombre (ES):** Nombre en español de la profesión. Campo obligatorio.
- **Nombre (EN):** Nombre en inglés (opcional, útil como referencia).
- **Tipo:** Básica o Avanzada.
- **Descripción:** Texto libre con la descripción de la profesión.
- **Imagen:** Foto o ilustración de la profesión (JPG, PNG, etc.).

**Perfil Principal** (características primarias, mejoras en porcentaje, múltiplos de 5)

| Sigla ES | Sigla EN | Nombre completo |
|---|---|---|
| HA | WS | Habilidad de Armas |
| HP | BS | Habilidad de Proyectiles |
| F | S | Fuerza |
| R | T | Resistencia |
| Ag | Ag | Agilidad |
| I | Int | Inteligencia |
| V | WP | Voluntad |
| Em | Fel | Empatía |

**Perfil Secundario** (características secundarias, mejoras en unidades)

| Sigla ES | Sigla EN | Nombre completo |
|---|---|---|
| A | A | Ataques |
| H | W | Heridas |
| BF | SB | Bonus de Fuerza |
| BR | TB | Bonus de Resistencia |
| M | M | Movimiento |
| Mag | Mag | Magia |
| PL | IP | Puntos de Locura |
| PD | FP | Puntos de Destino |

**Habilidades**

La sección de habilidades distingue dos tipos de entrada:

- **Habilidades simples:** Marca la casilla y opcionalmente rellena el campo **"Gr."** (grupo de elección) y **"Esp."** (especialización separada por comas).
- **Habilidades con especializaciones predefinidas** (Hablar Idioma, Oficio, Sabiduría Académica, etc.): muestran un panel expandible con tags clicables. Cada clic en un tag **añade una entrada** nueva con esa especialización; cada entrada tiene su propio campo **"Gr."**. Esto permite representar exactamente la estructura del libro:
  - *Hablar Idioma (Reikspiel o Tileano)* → dos entradas con el mismo grupo = el jugador elige una.
  - *Hablar Idioma (Bretón)* → una entrada con grupo distinto = obligatoria.
  - Los botones **Cualquiera / Dos cualquiera / Tres cualquiera** añaden entradas especiales para elecciones abiertas.

El campo **"Gr."** (grupo de elección) funciona igual para habilidades simples y con especializaciones: habilidades/entradas con el mismo número son alternativas (el jugador elige una). Déjalo vacío para elementos obligatorios.

**Talentos**
- Funciona igual que las habilidades simples. Usa el número de grupo para indicar elecciones tipo "Talento A o Talento B".
- El campo "Esp." permite especializaciones del mismo modo.

**Enseres**
- Lista separada por comas de los objetos necesarios para la profesión.
- Ejemplo: `Espada, Escudo, Armadura de malla, 10 coronas de oro`

**Salidas (Career Exits)**
- Marca las profesiones a las que se puede acceder al completar ésta.
- Los accesos (Career Entries) se derivan automáticamente de las salidas ya configuradas en otras profesiones.

---

### Gestionar habilidades y talentos

Ve a **Habilidades** o **Talentos** desde el menú principal.

#### Campos de Habilidades

| Campo | Descripción |
|---|---|
| **Nombre (ES)** | Nombre en español. Obligatorio. |
| **Nombre (EN)** | Nombre en inglés. Lo usa el sistema para enlazar habilidades al importar PDFs en inglés. |
| **Tipo** | Básica o Avanzada. |
| **Características** | Características de las que depende la habilidad (p.ej. `Empatía, Inteligencia`). Separadas por comas si hay varias. |
| **Talentos asociados** | Talentos que potencian o modifican esta habilidad. |
| **Descripción** | Texto completo de la habilidad según las reglas. |

#### Campos de Talentos

| Campo | Descripción |
|---|---|
| **Nombre (ES)** | Nombre en español. Obligatorio. |
| **Nombre (EN)** | Nombre en inglés. Lo usa el sistema para enlazar talentos al importar PDFs en inglés. |
| **Descripción** | Texto completo del talento según las reglas. |

#### Búsqueda y filtros

- **Buscador** en la parte superior: busca por nombre de forma predeterminada. Activa **"Todos los campos"** para buscar también en descripción, características y talentos asociados.
- **Filtro por tipo** (solo habilidades): filtra entre Básica, Avanzada o todas.
- **Filtro por característica** (solo habilidades): muestra solo las habilidades que dependan de una característica concreta (desplegable con todos los valores existentes en la BD).

#### Importar y exportar

Desde la página de listado de habilidades o talentos, usa los botones **Importar** y **Exportar**.

**Formatos soportados:** texto plano (`.txt`), CSV (`.csv`) y Excel (`.xlsx`).

##### Formato de texto — Talentos

```
Nombre: Talento de ejemplo
Descripción: Descripción completa del talento.

Nombre: Otro talento
Descripción: Su descripción.
```

Cada bloque va separado por una línea en blanco. Los nombres de campo son `Nombre:` y `Descripción:`.

##### Formato de texto — Habilidades

```
Nombre: Habilidad de ejemplo
Tipo: Básica
Características: Empatía
Descripción: Descripción completa.
Talentos asociados: Talento A, Talento B

Nombre: Otra habilidad
Tipo: Avanzada
Características: Inteligencia, Voluntad
Descripción: Su descripción.
Talentos asociados:
```

Cada bloque separado por línea en blanco. `Tipo` acepta `Básica` o `Avanzada` (insensible a mayúsculas). Si `Talentos asociados:` está vacío o ausente, se guarda `NULL`.

> **Recomendación:** Carga primero el catálogo completo de habilidades y talentos antes de importar PDFs, para que el sistema pueda enlazarlos automáticamente.

---

### Gestionar usuarios y permisos

Ve a **Admin → Usuarios**.

#### Lista de usuarios

Desde esta pantalla puedes:

- **Cambiar el rol** entre `usuario` y `admin` con el selector de la fila. Los administradores tienen acceso total y no están limitados por las plantillas ni los permisos individuales.
- **Ver la plantilla asignada** a cada usuario normal en la columna "Plantilla".
- **Activar/Desactivar** usuarios con el botón de pausa/play. Un usuario desactivado no puede iniciar sesión.
- **Editar los permisos** de un usuario con el icono de llave 🔑, que abre la pantalla de edición de permisos.
- **Eliminar** la cuenta de usuario permanentemente.

#### Edición de permisos de un usuario (`/admin/usuarios/<id>/permisos`)

Desde aquí puedes:

1. **Asignar una plantilla** al usuario (ver sección siguiente). La plantilla define el conjunto base de permisos.
2. **Activar permisos directos** adicionales, que se suman a los de la plantilla. Útil para dar acceso puntual a una función sin crear una nueva plantilla.
3. Ver los **permisos efectivos actuales** (unión de plantilla + directos) como referencia.

#### Plantillas de permisos (`/admin/plantillas`)

Las plantillas son conjuntos predefinidos de permisos que se pueden asignar rápidamente a varios usuarios. Ve a **Admin → Plantillas de permisos** (o desde el botón de la pantalla de usuarios).

Plantillas incluidas por defecto:

| Plantilla | Permisos incluidos |
|---|---|
| **Lector** | Ver profesiones · Ver habilidades · Buscador de caminos · Ver personajes |
| **Editor** | Todo lo anterior + Editar profesiones · Importar PDF · Editar habilidades · Editar personajes |
| **Gestor** | Todo lo anterior + Gestionar usuarios (asignar plantillas y permisos a otros) |

Puedes crear, editar y eliminar plantillas desde esa pantalla. Al eliminar una plantilla, los usuarios que la tenían asignada pierden los permisos que venían de ella (los permisos directos se mantienen).

#### Códigos de permisos disponibles

| Código | Descripción |
|---|---|
| `professions.view` | Consultar listado y detalle de profesiones |
| `professions.edit` | Crear, editar y eliminar profesiones |
| `professions.import` | Importar profesiones desde un PDF |
| `skills.view` | Consultar habilidades y talentos |
| `skills.edit` | Crear, editar y eliminar habilidades y talentos |
| `pathfinder.use` | Buscar rutas entre profesiones |
| `characters.view` | Consultar personajes propios |
| `characters.edit` | Crear y editar personajes propios |
| `users.manage` | Asignar plantillas y permisos a otros usuarios (no puede convertir en admin) |

> **Nota:** Los administradores (`role = admin`) tienen acceso completo a todas las funciones independientemente de los permisos asignados. El permiso `users.manage` permite a un usuario normal gestionar permisos de otros, pero no puede cambiar roles ni crear administradores.

---

## Guía de operación — Usuario

### Registro e inicio de sesión

1. Pulsa **Registrarse** en la barra de navegación.
2. Introduce usuario, email y contraseña (mínimo 6 caracteres).
3. Inicia sesión desde **Entrar**.

> Los usuarios recién registrados no tienen ningún permiso por defecto. Un administrador debe asignarles una plantilla o permisos directos desde **Admin → Usuarios**.

---

### Explorar profesiones

Ve a **Profesiones** en el menú principal.

- Filtra por tipo (**Básica / Avanzada**) o busca por nombre.
- Al entrar en una profesión verás todos sus detalles: perfil primario y secundario, habilidades con grupos de elección indicados como "Habilidad A **o** Habilidad B", talentos, enseres, y las profesiones de acceso y salida.
- Desde la ficha puedes lanzar el **Buscador de caminos** con esa profesión como punto de partida.

---

### Usar el Buscador de caminos

Ve a **Buscador** en el menú principal.

1. Selecciona la **profesión de inicio** (la que tiene el personaje ahora o la inicial).
2. Selecciona la **profesión de destino** (la que se quiere alcanzar).
3. Pulsa el botón de búsqueda.

El sistema muestra hasta **5 rutas posibles**, ordenadas de menor a mayor número de pasos.

Para cada ruta se muestra:

- **Ruta:** secuencia de profesiones (Ej.: Soldado → Mercenario → Veterano).
- **Totales acumulados:** el valor más alto que ofrece cualquier profesión del camino, para cada característica.
  - Las características **primarias** (HA, HP, F, R, Ag, I, V, Em) mejoran en pasos de 5 %.
  - Las características **secundarias** (A, H, BF, BR, M, Mag, PL, PD) mejoran en pasos de 1 unidad.
- **Detalle por paso:** despliega cada profesión del camino con sus características, habilidades, talentos y enseres. Todos los pasos pueden estar abiertos simultáneamente.
- **Resumen de habilidades/talentos:** listado completo de todo lo que se puede obtener durante el camino (incluyendo grupos de elección).

---

### Explorar habilidades y talentos

- Ve a **Habilidades** o **Talentos** en el menú.
- Busca por nombre (opción por defecto) o activa **"Todos los campos"** para buscar también en la descripción.
- En habilidades, filtra adicionalmente por tipo (Básica/Avanzada) o por característica asociada.
- Al entrar en una habilidad o talento, verás su descripción completa, características y talentos asociados, y la lista de **todas las profesiones que lo otorgan**.

---

### Crear y gestionar personajes

Ve a **Personajes → Nuevo personaje**.

1. Introduce el nombre, raza y género del personaje.
2. En la sección **Carrera Profesional**, añade las profesiones que ha tenido el personaje en orden cronológico usando el botón **Añadir profesión**.
3. La última profesión añadida se marca como "Actual".
4. Guarda el personaje.

Desde la ficha del personaje puedes ver las estadísticas de cada profesión en su carrera.

---

## Modelo de datos

```
users
  ├─ template_id → permission_templates   (plantilla de permisos asignada)
  ├─ user_permissions (M2M)               (permisos directos adicionales)
  └─ characters
       └─ character_professions  (lista ordenada de profesiones del personaje)
       └─ character_skills
       └─ character_talents

permissions                               (9 códigos de permiso disponibles)
permission_templates                      (conjuntos reutilizables de permisos)
template_permissions (M2M)                (permisos que incluye cada plantilla)

professions
  ├─ profession_skills    (skill_id + specialization + choice_group)
  │    Ejemplo: Hablar Idioma con specialization="Tileano" y otra fila
  │    con specialization="Estaliano" permiten guardar sub-habilidades
  │    múltiples de la misma habilidad base. Cuando varias entradas de la
  │    misma habilidad comparten choice_group, el jugador elige una.
  ├─ profession_talents   (talent_id + specialization + choice_group)
  ├─ profession_trappings (enseres requeridos)
  └─ career_exits         (salidas: relación auto-referencial many-to-many)

skills
  ├─ name_es, name_en
  ├─ is_advanced
  ├─ caracteristicas       (características de las que depende, sep. por comas)
  ├─ talentos_asociados    (talentos que la modifican, sep. por comas)
  └─ description

talents
  ├─ name_es, name_en
  └─ description

synonyms                   (diccionario para importación de PDFs)
  ├─ source  (término incorrecto/alternativo, en minúsculas)
  ├─ target  (nombre oficial en WFRP2 ES)
  ├─ is_prefix  (True = aplica también a "source (especialización)")
  └─ notes
```

### Regla de acumulación de características en el Buscador

Todas las características (primarias y secundarias) se acumulan de la misma forma: se muestra el **valor más alto** que ofrece cualquier profesión individual del camino. No se suman.

- **Perfil principal** (HA, HP, F, R, Ag, I, V, Em): mejoras en pasos de 5 %. Una profesión con +20 % en HA y otra con +10 % resulta en **+20 %** total (no +30 %).
- **Perfil secundario** (A, H, BF, BR, M, Mag, PL, PD): mejoras en pasos de 1 unidad. Una profesión con +2 Ataques y otra con +1 resulta en **+2** total (no +3).

### Grupos de elección (choice_group)

Cuando una profesión ofrece elegir entre habilidades o talentos (p.ej. "Juego **o** Chismear"), ambas se almacenan con el mismo número en el campo `choice_group`. En la interfaz se muestran separadas por la palabra **"o"**.

Las habilidades/talentos con `choice_group = NULL` son **obligatorias** (no hay elección).

El mismo mecanismo se aplica a las especializaciones: si una profesión permite "Hablar Idioma (Reikspiel **o** Tileano)", se almacenan dos filas de `profession_skills` para la misma habilidad, con el mismo `choice_group` y diferente `specialization`.

### Permisos y plantillas

Los permisos se implementan en tres niveles:

1. **Administrador** (`role = 'admin'`): acceso total sin restricciones.
2. **Plantilla** (`template_id`): asigna un conjunto predefinido de permisos a un usuario.
3. **Permisos directos** (`user_permissions`): permisos adicionales sobre la plantilla, asignados individualmente.

Los permisos efectivos de un usuario son la unión de los que vienen de su plantilla y los directos. La comprobación se realiza con `user.has_perm(code)` en el backend y con el decorador `@require_permission(code)` en las rutas que lo necesitan.

---

## Estructura del proyecto

```
ProfesionesWH/
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
├── docker-compose.yml      # Orquestación: app + MySQL
├── Dockerfile              # Imagen de la aplicación
├── entrypoint.sh           # Script de arranque: espera DB, migraciones, crea admin
├── requirements.txt        # Dependencias Python
├── run.py                  # Punto de entrada de la aplicación
└── app/
    ├── __init__.py         # Factory de la app Flask + comandos CLI (init-db, create-admin)
    ├── config.py           # Configuraciones por entorno
    ├── extensions.py       # Instancias de extensiones Flask
    ├── utils.py            # Decoradores: admin_required, require_permission; helpers
    ├── data/
    │   └── skill_specializations.json  # Especializaciones predefinidas por habilidad
    ├── models/
    │   ├── __init__.py     # Exporta todos los modelos para Flask-Migrate
    │   ├── permission.py   # Permission, PermissionTemplate + tablas M2M + seed data
    │   ├── user.py         # Usuario: rol, has_perm(), effective_perm_codes()
    │   ├── profession.py   # Profesión, ProfessionSkill, ProfessionTalent, Trapping
    │   ├── skill.py        # Habilidad
    │   ├── talent.py       # Talento
    │   ├── character.py    # Personaje y su carrera profesional
    │   └── synonym.py      # Diccionario de sinónimos para importación PDF
    ├── routes/
    │   ├── auth.py         # Login, registro, logout
    │   ├── main.py         # Página de inicio, errores, servicio de uploads
    │   ├── professions.py  # CRUD de profesiones (edición requiere professions.edit)
    │   ├── skills_talents.py  # CRUD de habilidades y talentos (edición requiere skills.edit)
    │   ├── pathfinder.py   # Buscador de caminos
    │   ├── characters.py   # Gestión de personajes
    │   └── admin.py        # Panel admin, usuarios, permisos, plantillas, PDF
    ├── services/
    │   ├── pdf_processor.py      # OCR, traducción y parsing de PDFs
    │   ├── translation_service.py # Detección de idioma y traducción
    │   ├── import_service.py     # Importación/exportación de habilidades y talentos
    │   └── pathfinder_service.py  # Construcción del grafo y BFS
    ├── templates/
    │   ├── base.html             # Layout base con nav adaptativo
    │   ├── admin/
    │   │   ├── dashboard.html
    │   │   ├── users.html                # Lista de usuarios con plantilla y acciones
    │   │   ├── user_edit.html            # Edición de permisos por usuario
    │   │   ├── permission_templates.html # Lista de plantillas de permisos
    │   │   ├── template_edit.html        # Crear/editar plantilla
    │   │   ├── synonyms.html
    │   │   ├── pdf_upload.html
    │   │   └── pdf_review.html
    │   └── ...                   # Resto de plantillas por módulo
    └── static/
        ├── css/custom.css        # Tema oscuro medieval WH
        └── js/main.js            # Scripts del cliente
```
