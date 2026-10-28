# Colección Marvel Universe (MAR)

Web para llevar la colección de las 100 cartas full art de **Marvel Universe (MAR)**:
1–40 vienen en sobres de *Marvel's Spider-Man* y 41–100 en sobres de *Marvel Super Heroes*.

- Imagen, edición, número, precio **Card Kingdom** (normal) y enlaces a Moxfield, Card Kingdom y Scryfall.
- Check "la tengo / no la tengo", barra de progreso y valor de lo que tienes, de lo que te falta y del set completo.
- Filtros (tengo / faltan, origen, color), buscador y orden por número, nombre o precio.
- Modo oscuro automático.
- Guardado local en el dispositivo y uso sin conexión (se instala en el iPhone como app).
- Sincronización opcional en la nube con un **Gist privado** de GitHub, más exportar/importar JSON.

## Estructura

```
index.html                         la web completa
sw.js                              service worker (modo sin conexión)
manifest.webmanifest, icon*.png    instalación como app
data/cards.json                    lo genera la tarea diaria (no lo edites a mano)
scripts/update_cards.py            descarga cartas (Scryfall) y precios (Card Kingdom / MTGJSON)
.github/workflows/update-prices.yml  tarea diaria de GitHub Actions
```

## 1. Publicar en GitHub Pages

1. Crea un repositorio nuevo en GitHub, por ejemplo `mar-collection` (puede ser público o privado; Pages en repositorio privado requiere plan de pago).
2. Sube todo el contenido de esta carpeta a la rama `main`, incluida la carpeta oculta `.github`:
   ```bash
   cd mar-collection
   git init && git add . && git commit -m "Colección MAR"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/mar-collection.git
   git push -u origin main
   ```
3. En el repositorio: **Settings → Pages → Build and deployment → Source: Deploy from a branch**, rama `main`, carpeta `/ (root)`. Guarda.
4. En **Settings → Actions → General → Workflow permissions**, marca **Read and write permissions** y guarda (la tarea diaria necesita escribir `data/cards.json`).
5. Ve a **Actions → Actualizar precios → Run workflow** para generar los precios por primera vez. Después se ejecuta solo todos los días.
6. La web queda en `https://TU_USUARIO.github.io/mar-collection/`.

Mientras no exista `data/cards.json`, la web carga las cartas directo desde Scryfall y muestra el precio de TCGplayer (en color ámbar con la etiqueta **TCG**). Cuando la tarea diaria corre, aparece el precio de Card Kingdom (etiqueta **CK**).

## 2. Instalar en el iPhone

Abre la URL en **Safari → botón Compartir → Agregar a pantalla de inicio**. Se abre como app, guarda la colección en el teléfono y funciona sin conexión (las imágenes que ya viste quedan en caché).

> Nota: iOS puede borrar los datos de una web que no se usa por varias semanas. La sincronización con Gist evita perder la colección por eso.

## 3. Activar la nube (Gist)

1. En GitHub: **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
2. Nombre: `mar-collection`. Expiración: la que prefieras (por ejemplo, "No expiration" o 1 año). Marca **solo** el permiso `gist`. Genera y copia el token.
3. En la web, toca **Nube**, pega el token y toca **Guardar y sincronizar**. La primera vez se crea un Gist privado llamado `mar-collection.json`.
4. Repite el paso 3 en cada dispositivo (iPhone, computador). La web encuentra el mismo Gist automáticamente.

Cómo funciona: cada cambio se sube unos segundos después, y al abrir la app se descargan los cambios de otros dispositivos. Cada carta guarda la hora de su último cambio, así que si marcas cartas distintas en dos dispositivos no se pisan.

El token queda guardado solo en el navegador de cada dispositivo; nunca se sube al repositorio. Como solo tiene permiso `gist`, no puede tocar tus repositorios.

## Precios

- La tarea diaria toma el precio **normal (no foil)** de la lista de precios pública de Card Kingdom, cruzando por el ID de Scryfall. Si una variante tiene varias filas, usa la más barata.
- Si esa lista falla, usa como respaldo los precios de Card Kingdom publicados por MTGJSON.
- Si una carta no tiene precio en Card Kingdom ese día, se mantiene el último precio conocido; si nunca lo tuvo, se muestra TCGplayer marcado como **TCG**.
- Para cambiar la hora de ejecución, edita el `cron` en `.github/workflows/update-prices.yml` (está en UTC).

## Enlace a Moxfield

Moxfield no expone un identificador de carta que se pueda obtener desde Scryfall, por eso el enlace de cada carta abre la búsqueda de Moxfield por nombre. Si quieres otro formato, cambia `moxfieldCardUrl` en el bloque `CONFIG` al inicio del script de `index.html`.
