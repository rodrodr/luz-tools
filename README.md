# luz-mcp · Segunda República

**Español** · [English](#english)

Servidor MCP para consultar, desde Claude, ChatGPT, Cursor, Antigravity, OpenCode o cualquier
asistente de IA compatible, dos conjuntos de datos del Congreso de los Diputados de la Segunda
República española:

- **[Luz y Taquígrafos](https://doi.org/10.7910/DVN/THQCMI)**: los debates del pleno de 1931 a 1939,
  más cinco sesiones del exilio en 1945. Son 121 700 filas en 755 sesiones, cada intervención con su
  diputado.
- **[Afinidades Elegidas](https://doi.org/10.7910/DVN/CGOCUS)**: las 1 560 iniciativas firmadas
  colectivamente, con su texto íntegro, sus 13 028 firmas, la red de coautorías y sus métricas de
  red publicadas.

Los dos están en Harvard Dataverse con licencia CC BY 4.0, y el servidor los cruza: de una medida
salta al debate en que se leyó y se defendió, y de la posición de un diputado en la red, a lo que
dijo en el pleno.

## Instalación

Requisito: [uv](https://docs.astral.sh/uv/getting-started/installation/).

**Claude Code**

```bash
claude mcp add luz -s user -- uvx luz-mcp
```

**Otros clientes** (bloque `mcpServers` de su configuración):

```json
{ "mcpServers": { "luz": { "command": "uvx", "args": ["luz-mcp"] } } }
```

Los datos se descargan una vez, con la herramienta `download_data` o desde la terminal. Son unos
210 MB y se guardan en `~/.luz`, o en la carpeta que indique `LUZ_HOME`:

```bash
uvx luz-mcp download
```

## Qué se puede preguntar

- *«¿Cómo evoluciona "reforma agraria" frente a "orden público" entre 1931 y 1936?»*: `ngram_viewer`
- *«¿Qué familias políticas hablan más de lo que les corresponde por escaños en las Constituyentes?»*:
  `share_of_voice`
- *«¿Qué palabras distinguen a los socialistas de los conservadores, sin la presidencia?»*:
  `distinctive_words`
- *«Busca las enmiendas de tema agrario defendidas en el pleno y enséñame el debate»*:
  `search_measures` y `get_measure`
- *«¿Entre qué familias se firman más iniciativas conjuntas en la segunda legislatura?»*:
  `cross_group_coauthorship`
- *«¿Hablan distinto en el pleno los diputados que articulan la red y los que se quedan en su
  partido?»*: `speech_by_network` y `distinctive_words`

## Herramientas

| grupo | herramientas |
|---|---|
| datos | `list_datasets` · `download_data` · `get_documentation` · `how_to_cite` · `describe_data` |
| discurso | `coverage` · `ngram_viewer` · `term_counter` · `term_frequency` · `share_of_voice` · `distinctive_words` · `kwic` · `collocations` · `search_text` · `get_intervention` · `get_session` |
| bibliotecas | `library_create` · `library_describe` · `library_edit` · `library_combine` · `library_rebuild` · `library_delete` · `library_export` · `library_import` |
| medidas | `search_measures` · `get_measure` |
| red | `coauthorship_network` (exporta GraphML o CSV para Gephi, igraph o R) · `deputy_neighbors` · `cross_group_coauthorship` |
| métricas | `network_metrics` · `structural_roles` (las publicadas, sin recalcular) |
| discurso × red | `speech_by_network` · `deputy_profile` |
| reproducibilidad | `query_sql` (SQL de solo lectura) · `export_result` · `query_log` |

## Lo que conviene saber

- **No hay variable de sexo** en ninguno de los dos conjuntos, así que nada se desglosa por sexo.
- **No todo es discurso.** `SUMARIO`, el sumario de cada sesión, y `COMENTARIOS`, que son documentos
  leídos, votaciones y la narración del Diario, son `dm_speech = 0`.
- **Hay dos juegos de etiquetas.** El de Luz y Taquígrafos (`party`, `party_family`, `ideology`) y el
  del registro revisado de Afinidades (`reg_party`, `reg_family`, `reg_ideology`). Para comparar voz
  y escaños se usan los segundos, porque son los que comparte la lista de miembros. Los ministros
  que hablan en una legislatura en la que no tenían escaño no tienen etiqueta de registro.
- **La misma legislatura se rotula distinto.** Luz y Taquígrafos dice 1933-1935 y Afinidades,
  1933-1936.
- **Las métricas y roles de red son los publicados.** Al cargar los datos, el grado de cada
  diputado se recalcula desde la lista de aristas y se comprueba que coincide.
- **Algunas listas de firmas están truncadas en el Diario,** y a esas medidas les faltan aristas.
- **La presidencia queda fuera de `speech_by_network` por defecto.** No firma iniciativas, así que
  aparece entre los diputados aislados de la red, pero habla en todas las sesiones para dar la
  palabra.
- **Bibliotecas y explorador.** Las bibliotecas se exportan para el
  [explorador de Luz y Taquígrafos](https://rodrodr.github.io/luz_explorer) con los números de
  fila de la **versión 3**. Hay que importarlas allí con el CSV de la versión 3 cargado: el
  explorador acepta también la versión 2, y en ella los mismos números son otras intervenciones.

## Cómo está hecho

luz-mcp es un perfil del motor de [parlaibero-mcp](https://github.com/rodrodr/parlaibero-tools), el
servidor de los 16 parlamentos iberoamericanos. La búsqueda, los recuentos, las bibliotecas y la
exportación son el mismo código. Este paquete añade:

- cómo se leen los dos conjuntos;
- las tablas de Afinidades;
- las herramientas de medidas y red.

```bash
uv run --with pytest pytest     # pruebas sin red
```

## Cita y licencia

Cite cada conjunto con su versión (`how_to_cite`):

- Rodrigues-Silveira, R.; García-Díez, F.; Llamazares, I.; Martínez-Barahona, E.; Barreto Martín,
  E. (2026). *Luz y Taquígrafos: Parliamentary Debates in the Second Spanish Republic, 1931–1945*.
  Harvard Dataverse. https://doi.org/10.7910/DVN/THQCMI
- Rodrigues-Silveira, R.; García-Díez, F.; Llamazares, I.; Martínez-Barahona, E.; Barreto Martín,
  E. (2026). *Afinidades Elegidas: Parliamentary Cosponsorship Networks of the Spanish Second
  Republic (1931-1939)*. Harvard Dataverse. https://doi.org/10.7910/DVN/CGOCUS

El código tiene licencia MIT, y los datos, CC BY 4.0.

---

## English

An MCP server to query two datasets on the Congress of Deputies of the Spanish Second Republic
from Claude, ChatGPT, Cursor, Antigravity, OpenCode or any MCP-capable assistant:

- **[Luz y Taquígrafos](https://doi.org/10.7910/DVN/THQCMI)**: the plenary debates, 1931-1939, plus
  five sessions in exile in 1945. That is 121,700 rows in 755 sessions, each intervention linked to
  its deputy.
- **[Afinidades Elegidas](https://doi.org/10.7910/DVN/CGOCUS)**: the 1,560 collectively signed
  initiatives, with their full text, 13,028 signatures, the co-authorship network and its published
  network metrics.

Both are in Harvard Dataverse under CC BY 4.0, and the server joins them. From a measure it jumps
to the debate where the measure was read and defended; from a deputy's position in the network, to
what that deputy said on the floor.

```bash
claude mcp add luz -s user -- uvx luz-mcp     # Claude Code
uvx luz-mcp download                          # the data, once (about 210 MB, in ~/.luz)
```

The tools are listed in the table above. What to keep in mind:

- **There is no sex variable.**
- **Not all rows are speech.** `SUMARIO` and `COMENTARIOS` rows have `dm_speech = 0`.
- **There are two sets of party labels.** Compare voice with seats using the `reg_*` labels, those
  of the revised register.
- **The two datasets label the second legislature differently:** 1933-1935 and 1933-1936.
- **The network metrics are the published ones,** checked on import against the edge list.
- **Some signature lists are truncated.**
- **The chair is left out of `speech_by_network` by default.** It signs no initiatives but speaks
  in every sitting.
- **Libraries are written for the Luz y Taquígrafos explorer with the row numbers of version 3.**
  Import them there only with the version 3 CSV loaded.

luz-mcp is a profile of the [parlaibero-mcp](https://github.com/rodrodr/parlaibero-tools) engine.
The code is MIT-licensed; the data are CC BY 4.0. Cite each dataset with its version.
