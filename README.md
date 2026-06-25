# Gestor de Profesiones — Warhammer Fantasy Roleplay

Aplicación web para gestionar profesiones, habilidades, talentos y personajes del juego de rol **Warhammer Fantasy Roleplay (2ª edición)**. Permite importar profesiones desde PDFs del libro de reglas (incluyendo páginas escaneadas en inglés o español), buscar rutas de progresión entre profesiones y crear personajes.

---

## Tabla de contenidos

- [Características](#características)
- [Tecnologías](#tecnologías)
- [Instalación rápida con Docker](#instalación-rápida-con-docker)
- [Instalación local para desarrollo](#instalación-local-para-desarrollo)
- [Configuración](#configuración)
- [Guía de operación — Administrador](#guía-de-operación--administrador)
- [Guía de operación — Usuario](#guía-de-operación--usuario)
- [Modelo de datos](#modelo-de-datos)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Características

| Módulo | Descripción |
|---|---|
| **Profesiones** | Catálogo con todos los campos WFRP2: perfil primario y secundario, habilidades, talentos, enseres, accesos y salidas |
| **Importación PDF** | Sube un PDF del libro (escaneado o digital), con OCR automático y traducción inglés → español |
| **Buscador de caminos** | Encuentra hasta 5 rutas entre dos profesiones mostrando características acumuladas, habilidades y enseres necesarios en cada paso |
| **Habilidades y Talentos** | Catálogo completo con buscador avanzado (nombre / todos los campos); importación y exportación en texto, CSV y Excel; filtros por tipo (Básica / Avanzada) y por característica asociada; cada entrada muestra qué profesiones la otorgan |
| **Personajes** | Crea personajes asignándoles una carrera profesional con múltiples profesiones en orden |
| **Roles de usuario** | Administradores (gestión completa) y usuarios normales (consulta y personajes propios) |

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
# Inicializa las migraciones (solo la primera vez)
flask db init
flask db migrate -m "initial schema"
flask db upgrade

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
- Marca la casilla de cada habilidad que otorgue la profesión.
- El campo **"Gr."** (grupo) sirve para las elecciones opcionales: si dos habilidades tienen el mismo número de grupo, el jugador elige una de ellas. Déjalo vacío para habilidades obligatorias.
- Ejemplo: _Juego_ y _Chismear_ con grupo `1` → el jugador elige una de las dos.

**Talentos**
- Funciona igual que las habilidades. Usa el número de grupo para indicar elecciones tipo "Talento A o Talento B".

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

### Gestionar usuarios

Ve a **Admin → Usuarios**.

- **Rol:** Cambia entre `usuario` y `admin` con el selector de la fila.
- **Activar/Desactivar:** Usa el botón de pausa/play para bloquear el acceso sin eliminar la cuenta.
- **Eliminar:** Elimina permanentemente la cuenta y todos sus personajes.

---

## Guía de operación — Usuario

### Registro e inicio de sesión

1. Pulsa **Registrarse** en la barra de navegación.
2. Introduce usuario, email y contraseña (mínimo 6 caracteres).
3. Inicia sesión desde **Entrar**.

---

### Explorar profesiones

Ve a **Profesiones** en el menú principal.

- Filtra por tipo (**Básica / Avanzada**) o busca por nombre.
- Al entrar en una profesión verás todos sus detalles: perfil primario y secundario, habilidades (con grupos de elección indicados como "Habilidad A **o** Habilidad B"), talentos, enseres, y las profesiones de acceso y salida.
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
- **Totales acumulados:** características del perfil completo al finalizar el camino.
  - Las características **primarias** (%) muestran el **valor máximo** de cualquier profesión del camino (no se suman).
  - Las características **secundarias** (unidades) se **suman** a lo largo del camino.
- **Detalle por paso:** despliega cada profesión del camino con sus características, habilidades, talentos y enseres necesarios.
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
  └─ characters
       └─ character_professions  (lista ordenada de profesiones del personaje)
       └─ character_skills
       └─ character_talents

professions
  ├─ profession_skills    (habilidades con choice_group para elecciones OR)
  ├─ profession_talents   (talentos con choice_group para elecciones OR)
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
```

### Regla de acumulación de características en el Buscador

- **Perfil principal** (HA, HP, F, R, Ag, I, V, Em): Se muestra el **valor más alto** de cualquier profesión del camino. Una profesión con +20% en HA y otra con +10% resulta en +20% total (no +30%).
- **Perfil secundario** (A, H, BF, BR, M, Mag, PL, PD): Se **suman** todas las mejoras a lo largo del camino.

### Grupos de elección (choice_group)

Cuando una profesión ofrece elegir entre habilidades o talentos (p.ej. "Juego **o** Chismear"), ambas se almacenan con el mismo número en el campo `choice_group`. En la interfaz se muestran separadas por la palabra **"o"**.

Las habilidades/talentos con `choice_group = NULL` son **obligatorias** (no hay elección).

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
    ├── __init__.py         # Factory de la app Flask
    ├── config.py           # Configuraciones por entorno
    ├── extensions.py       # Instancias de extensiones Flask
    ├── utils.py            # Decoradores y helpers (admin_required, etc.)
    ├── models/
    │   ├── user.py         # Modelo de usuario y carga de sesión
    │   ├── profession.py   # Profesión, ProfessionSkill, ProfessionTalent, Trapping
    │   ├── skill.py        # Habilidad
    │   ├── talent.py       # Talento
    │   └── character.py    # Personaje y su carrera profesional
    ├── routes/
    │   ├── auth.py         # Login, registro, logout
    │   ├── main.py         # Página de inicio, errores, servicio de uploads
    │   ├── professions.py  # CRUD de profesiones
    │   ├── skills_talents.py  # CRUD de habilidades y talentos + detalle
    │   ├── pathfinder.py   # Buscador de caminos
    │   ├── characters.py   # Gestión de personajes
    │   └── admin.py        # Panel de admin, usuarios, importación PDF
    ├── services/
    │   ├── pdf_processor.py      # OCR, traducción y parsing de PDFs
    │   ├── translation_service.py # Detección de idioma y traducción
    │   ├── import_service.py     # Importación/exportación de habilidades y talentos
    │   └── pathfinder_service.py  # Construcción del grafo y BFS
    ├── templates/          # Plantillas Jinja2 (Bootstrap 5)
    └── static/
        ├── css/custom.css  # Tema oscuro medieval WH
        └── js/main.js      # Scripts del cliente
```
