# Plan · MCP de *Luz y Taquígrafos* y *Afinidades Elegidas*

> **Estado: CONSTRUIDO** (2026-10-04), fases A, C, D y E; faltan la B y la F (publicar
> parlaibero-mcp 0.4.0 y luz-mcp 0.1.0, que publica el investigador, y crear el repositorio).

**Resultado de las puertas (2026-10-04):**
1. parlaibero-mcp 0.4.0: 38 pruebas; la batería de 21 llamadas da la misma salida que la 0.3.0. La única
   diferencia era el orden de los empates de `term_frequency(by='session')`, arbitrario ya en la 0.3.0, y
   se ha fijado.
2. Las cifras publicadas se reproducen todas:
   - Luz y Taquígrafos: 121 700 filas, 755 sesiones y 108 291 de discurso;
   - Afinidades Elegidas: 1 560 medidas, 13 028 firmas, 65 051 aristas, 1 446 fichas, 1 026 diputados,
     912 con coautoría y 782 medidas defendidas.
3. Comprobaciones independientes, todas a cero o completas:
   - ninguna fila de inicio o de defensa falta ni cae en otra fecha;
   - ningún defensor es otro diputado;
   - el grado recalculado coincide en los 2 128 diputados-periodo;
   - los roles concuerdan con las métricas.

   440 filas de habla de 14 personas que hablan en una legislatura sin escaño en ella (ministros) no
   tienen etiqueta de registro, y así se declara.
4. Ida y vuelta contra el motor real del explorador de Luz: **carga la V3 sin avisos** (121 700 filas) e
   importa y reexporta una biblioteca del MCP sin una sola diferencia (605 items), reconociendo la fuente.
   Por eso el corpus se llama `2REP_Diaries`, como en el explorador, y la decisión (a) no exige cambiarlo:
   basta con cargar allí la V3.
5. 8 pruebas sin red de luz-mcp y una prueba de punta a punta por el protocolo MCP con las 36
   herramientas.

Hallazgo de las pruebas: en `speech_by_network`, la presidencia de la Cámara cae entre los diputados
aislados (no firma) y les daba 21 774 turnos; sin ella son 77. La presidencia queda fuera por defecto
(`exclude_chair`).
> Decidido por el investigador: un **servidor propio** que reutiliza el **motor de parlaibero-mcp** (sin copiarlo),
> en un **repositorio nuevo**, con las cuatro familias de herramientas de *Afinidades Elegidas*: medidas y firmas,
> red de coautorías, métricas y roles, y discurso × red.

---

## 1. Qué hay, medido hoy en Dataverse (solo lectura)

**Luz y Taquígrafos** — doi:10.7910/DVN/THQCMI, **V3 publicada hoy** (2026-10-03 13:39 UTC), CC BY 4.0.

- Un solo archivo de datos, `2REP_Diaries.csv`: 173 899 410 bytes, MD5 `1cc232de…`, separador `;`, todo entre
  comillas, 14 columnas: `id, num_session, order, date, speaker, speech, rep_id, rep_name, district, party,
  party_family, ideology, nwords, legislature`. Más `mapa_v2_v3.json` (12,8 MB), que traduce cada fila de la V3 a
  la fila y el tramo de la V2.
- 121 700 filas en 755 sesiones, de 1931-07-14 a 1945-11-09 (cinco sesiones del exilio en México).
- `speaker = "SUMARIO"` (755 filas, `order` 0) y `"COMENTARIOS"` (12 654 filas) marcan lo que no es discurso.
- **Medido en un borrador local:** en él, `id` coincidía fila a fila con el número de registro del archivo, y
  `num_session` se reinicia en cada legislatura (405 valores para 755 sesiones). La clave de una sesión es, por
  tanto, `(legislature, num_session)`. Esto se vuelve a medir sobre el archivo publicado al construir.
- **No tiene variable de sexo.** El padrón de diputados «está disponible a petición»: no se publica.

**Afinidades Elegidas** — doi:10.7910/DVN/CGOCUS, V2 publicada hoy (archivos con sufijo `_v3`), CC BY 4.0.

- `2REP_measures_v3.csv`: 1 560 medidas con texto íntegro, título, tema (13 categorías), primer autor, defensa en
  el pleno, y las filas de *Luz y Taquígrafos* donde empieza el texto (`diaries_id_inicio`) y donde se defiende
  (`diaries_id_defensa`).
- `2REP_cosponsorship_v3.csv` (13 028 firmas, con `truncada` cuando el Diario no reproduce todas),
  `2REP_coauthor_edgelist_v3.csv` (65 051 pares por medida), `representative_metadata_v3.csv` (1 446 fichas
  diputado-legislatura de 1 026 diputados: partido, familia, ideología, distrito, variantes del nombre; **sin
  sexo**), `representatives_metrics_v3.json` (centralidades, Guimerà-Amaral, ego-redes, perfiles y roles por
  diputado y periodo, más proximidades y comunidades por partido y familia), `representatives_roles_v3.json`,
  diccionarios de partidos y temas, y los registros de correcciones.

**Cómo se enlazan.** El `rep_id` de *Luz y Taquígrafos* es el `id_dip` de *Afinidades*: se comprobaron 400 de 400.
Las medidas apuntan a filas de la V3 (`diaries_id_*`).

Tres desajustes que el MCP tiene que resolver, y decir:

1. **Las etiquetas de legislatura no coinciden.** *Luz* usa `1933-1935`; *Afinidades*, `1933-1936`. Se cruza por
   fecha, no por etiqueta.
2. **El explorador web público de *Luz* lee la V2**, no la V3: reconoce el archivo de 165 785 782 bytes y su
   número de fila es el de la V2. Una biblioteca exportada con números de la V3 apuntaría allí a otras
   intervenciones. (§6)
3. **Su `2REP_Diaries_v3.csv` local no es el publicado** (MD5 distinto: es un borrador anterior a la
   normalización de etiquetas). El MCP descarga siempre de Dataverse.

---

## 2. Arquitectura

```
parlaibero-mcp 0.4.0  (repo parlaibero-tools, PyPI)
  └─ motor generalizado: almacén, búsqueda, conteo, ngram, kwic, colocaciones, distinctive_words,
     share_of_voice, bibliotecas, exportación — parametrizado por un PERFIL DE COLECCIÓN
     ├─ perfil «parlaibero»   (los 16 países; comportamiento idéntico al de hoy, con las 38 pruebas de guarda)
     └─ (expone el perfil como API para otros paquetes)

luz-mcp 0.1.0  (repo nuevo, PyPI; depende de parlaibero-mcp >=0.4,<0.5)
  ├─ perfil «luz»: catálogo (2 DOI), lectura del CSV `;`, mapeo de columnas, filtros propios
  │   (party_family, ideology), instrucciones del servidor, formato del explorador de Luz
  ├─ tablas de Afinidades (medidas, firmas, aristas, métricas, roles, diccionarios)
  └─ herramientas de Afinidades (§4)
```

**El perfil de colección** es lo único nuevo en parlaibero-mcp. Reúne:

- el catálogo de conjuntos, con sus DOI y archivos;
- cómo se lee cada CSV (separador y columnas) y cómo se mapea a las columnas canónicas;
- qué filas no son discurso;
- las columnas extra que se pueden filtrar;
- el texto de instrucciones del servidor;
- el directorio del almacén;
- el formato de biblioteca del explorador (nombre del corpus y número de fila).

ParlaIbero pasa a ser el primer perfil, y su comportamiento no cambia: lo vigilan las 38 pruebas actuales, más una
que compara herramienta por herramienta la 0.3.0 con la 0.4.0 sobre la misma base.

**Mapeo de *Luz y Taquígrafos* al esquema del motor:**

| motor | Luz y Taquígrafos |
|---|---|
| `id_int` | `LT` + `id` con ceros, para que sea único y legible: `LT0075580` |
| `row_n` | `id`, el número de registro, comprobado contra el archivo como en ParlaIbero |
| `id_session` | `LT` + legislatura + `num_session` |
| `intervention_order` | `order` |
| `speaker_raw` · `id_dep` · `speaker_name` | `speaker` · `rep_id` · `rep_name` |
| `party` · `district` · `legislature` · `date` · `text` | `party` · `district` · `legislature` · `date` · `speech` |
| `dm_speech` | `0` si `speaker` es `SUMARIO` o `COMENTARIOS`; `1` en el resto |
| `sex` | vacío: no existe; el servidor lo dice y no ofrece análisis por sexo |
| extra | `party_family`, `ideology` (filtrables y como grupo en `share_of_voice` y `distinctive_words`) |

`n_words` se recalcula con la definición del motor, y la columna `nwords` publicada se conserva aparte, para que
cualquiera pueda contrastar las dos.

Almacén propio en `~/.luz` (`LUZ_HOME`), separado del de ParlaIbero, con sus bibliotecas en su propio archivo.

---

## 3. Herramientas heredadas del motor

Funcionan igual que en ParlaIbero:

- **búsqueda y lectura:** `search_text`, `get_intervention`, `get_session`;
- **recuentos en el tiempo:** `ngram_viewer` (por año o por legislatura), `term_counter`, `term_frequency`;
- **comparación y contexto:** `distinctive_words` (también por familia e ideología), `share_of_voice` (por partido,
  familia o ideología, nunca por sexo), `kwic`, `collocations`;
- **control de la base:** `coverage`;
- **SQL, exportación y trazabilidad:** `query_sql`, `export_result`, `query_log`;
- **las ocho herramientas de bibliotecas.**

---

## 4. Herramientas de *Afinidades Elegidas* (nuevas)

**Medidas y firmas**

- `search_measures`: por tema principal o secundario, tipo, legislatura, fechas, firmante, primer autor, partido o
  familia de los firmantes, defensa en el pleno, o texto. Devuelve título, tema, firmas y defensa.
- `get_measure`: el texto íntegro, los firmantes (marcando las firmas ilegibles y las listas truncadas) y la
  defensa. **Salta al debate:** devuelve la intervención de *Luz y Taquígrafos* donde se lee la medida y la de su
  defensa, con los turnos de alrededor.

**Red de coautorías**

- `coauthorship_network`: la red de una legislatura, de un tema o de un conjunto de medidas. Dice nodos, aristas,
  densidad y componentes, y la escribe en GraphML o en CSV de aristas y nodos, para Gephi, igraph o R.
- `deputy_neighbors`: la ego-red de un diputado (coautores, peso y partido), por legislatura.
- `cross_group_coauthorship`: coautorías entre partidos, familias o ideologías. Para cada par de grupos, observado
  frente a esperado e índice E-I. Las proximidades publicadas por partido y familia se leen, no se recalculan.

**Métricas y roles** (las publicadas; **no se recalculan**)

- `network_metrics`: las métricas de un diputado por periodo, o el ranking de una métrica (centralidades,
  Guimerà-Amaral, ego-redes, perfiles) con filtros por partido, familia o legislatura.
- `structural_roles`: la distribución de los seis roles por partido, familia o legislatura, y quién ocupa cada
  rol.

Antes de dar por buena la tabla, una comprobación independiente recalcula el grado de cada diputado desde la lista
de aristas y lo compara con el publicado.

**Discurso × red**

- `speech_by_network`: une a cada diputado su rol o una métrica, y lo que dijo en el pleno. Por ejemplo:
  - cuánto hablan los diputados puente frente a los periféricos;
  - qué palabras los distinguen (`distinctive_words` entre los dos grupos);
  - qué temas defienden en el pleno.

  Lo hace construyendo **bibliotecas** con las intervenciones de cada grupo, de modo que todas las herramientas
  de texto sirven después sobre ellas.
- `deputy_profile`: la ficha completa de un diputado: legislaturas y partido, cuánto habla y en qué sesiones, sus
  medidas (firmadas, primeras firmas, defendidas), su posición en la red y su rol.

---

## 5. Avisos que el servidor da al agente

- **No hay variable de sexo** en ninguno de los dos conjuntos: nada se analiza por sexo, y se dice si se pide.
- **Lo que no es discurso:** `SUMARIO` y `COMENTARIOS` (lecturas de documentos, votaciones, narración del Diario)
  son `dm_speech = 0`.
- **Las listas de firmas truncadas** (`truncada`) dejan incompleta la red de esa medida, y el servidor la marca
  donde pesa.
- **Tema, título y defensa** se asignaron con modelos de lenguaje y revisión humana, según la metodología
  publicada. El tema es una clasificación, no un dato del Diario.
- **Las etiquetas de legislatura difieren** entre los dos conjuntos.
- **Las sesiones del exilio de 1945** se tratan como una base escasa.
- **Los identificadores solo son estables dentro de una versión:** se cita siempre la versión, y la V2 se traduce
  con el mapa.

---

## 6. Bibliotecas y el explorador de *Luz*

El explorador de escritorio guarda las bibliotecas como `2replib/1`, con `corpus = "2REP_Diaries_v3"` y `speech_id`
igual al número de fila: es el formato de partida del de ParlaIbero. El explorador web público, en cambio, **lee la
V2**. Hay tres caminos (decisión 2 del §9):

- **(a) Solo V3.** Las bibliotecas se exportan con números de la V3. Sirven en cuanto el explorador lea la V3, lo
  que exige actualizarlo aparte: es un cambio en otro repositorio.
- **(b) V3 y traducción a la V2 con `mapa_v2_v3.json`.** Al exportar para un explorador en V2, cada intervención de
  la V3 se lleva a la fila de la V2 que la contiene. Es una traducción con pérdida: varias filas de la V3 pueden
  caer en la misma de la V2. Al importar desde la V2, una fila se abre en todas sus piezas de la V3. El informe
  dice cuántas se fundieron o se abrieron.
- **(c) No exportar al explorador de Luz por ahora;** solo CSV o Parquet.

Recomendación: **(b)** mientras el explorador siga en la V2, y **(a)** cuando pase a la V3. El código de traducción
es pequeño, porque el mapa ya está publicado.

---

## 7. Puertas antes de publicar

1. **parlaibero-mcp 0.4.0 no cambia ningún resultado.** Las 38 pruebas pasan, y la comparación herramienta por
   herramienta entre 0.3.0 y 0.4.0, sobre BR, ES y SV, da salidas idénticas.
2. **Las cifras publicadas se reproducen:**
   - *Luz y Taquígrafos*: 121 700 filas, 755 sesiones, 755 `SUMARIO` y 12 654 `COMENTARIOS`;
   - *Afinidades Elegidas*: 1 560 medidas, 13 028 firmas, 65 051 aristas, 1 446 fichas y 912 diputados con al
     menos una coautoría;
   - el MD5 de cada archivo es igual al de Dataverse.
3. **Comprobaciones independientes:**
   - el grado recalculado desde las aristas coincide con el publicado;
   - cada `diaries_id_inicio` y `diaries_id_defensa` existe y cae en la sesión y la fecha de su medida;
   - el número de fila coincide con el archivo.
4. **Ida y vuelta de bibliotecas contra el motor real del explorador de Luz**, como con ParlaIbero, según la
   opción que se elija en el §6.
5. **Prueba de punta a punta por el protocolo MCP**, más pruebas sin red con un corpus sintético.
6. **README:** sin nombres de parlamentarios en los ejemplos (norma de divulgación del proyecto: cargo, partido y fecha), y
   con la mención de financiación que corresponda (decisión 3 del §9).

---

## 8. Fases

| fase | contenido | dónde |
|---|---|---|
| A | perfil de colección en el motor; ParlaIbero como primer perfil; la comparación 0.3 = 0.4 | parlaibero-tools |
| B | publicar parlaibero-mcp 0.4.0 (la publica usted) | PyPI |
| C | luz-mcp: perfil, descarga, importación, herramientas heredadas, avisos | repositorio nuevo |
| D | tablas y herramientas de Afinidades; discurso × red | repositorio nuevo |
| E | bibliotecas y explorador de Luz (§6); puertas del §7 | ambos |
| F | README ES/EN, CITATION, publicar luz-mcp 0.1.0 (lo publica usted) | repositorio nuevo, PyPI |

---

## 9. Decisiones (del investigador, 3-oct)

1. **Nombre:** paquete `luz-mcp` (`uvx luz-mcp`), repositorio `rodrodr/luz-tools`.
2. **Explorador de Luz: (a), solo V3.** Las bibliotecas se exportan con los números de fila de la V3; sirven en el
   explorador cuando este lea la V3 (cambio aparte, en su repositorio). No se traduce a la V2.
3. **Sin mención de financiación.**
4. **Instrucciones del servidor en inglés**; README en español e inglés.
