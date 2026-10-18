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

Requisito: [uv](https://docs.astral.sh/uv/getting-started/installation/). El paquete está en
[PyPI](https://pypi.org/project/luz-mcp/), así que no hace falta clonar nada.

**Claude Code**

```bash
claude mcp add luz -s user -- uvx luz-mcp
```

**Codex CLI**

```bash
codex mcp add luz -- uvx luz-mcp
```

**ChatGPT de escritorio** y **Codex** comparten un mismo archivo de configuración,
`~/.codex/config.toml`. La orden anterior lo escribe; también puede añadirse a mano:

```toml
[mcp_servers.luz]
command = "uvx"
args = ["luz-mcp"]
```

ChatGPT en la web solo admite servidores remotos, así que no puede usar este.

**OpenCode** (`~/.config/opencode/opencode.json`, dentro del bloque `"mcp"`, junto a los servidores
que ya tenga):

```json
{
  "mcp": {
    "luz": { "type": "local", "command": ["uvx", "luz-mcp"], "enabled": true }
  }
}
```

**Antigravity** (`~/.gemini/config/mcp_config.json`, o *MCP Servers → Manage → View raw config*),
**Claude Desktop** (`claude_desktop_config.json`), **Cursor** (`~/.cursor/mcp.json`), **Gemini CLI**
(`~/.gemini/settings.json`), **Windsurf** y la mayoría de los demás clientes usan este bloque:

```json
{
  "mcpServers": {
    "luz": {
      "command": "uvx",
      "args": ["luz-mcp"]
    }
  }
}
```

Hay que reiniciar el cliente después de cambiar la configuración. Las aplicaciones de escritorio no
siempre ven el `PATH` de la terminal: si el servidor no arranca, cambie `"uvx"` por la ruta completa
que da `which uvx` (por ejemplo, `/Users/usted/.local/bin/uvx`).

Los datos se descargan una vez, con la herramienta `download_data` o desde la terminal. Son unos
210 MB y se guardan en `~/.luz`, o en la carpeta que indique `LUZ_HOME`. Con modelos locales, que
son más lentos, conviene descargarlos desde la terminal para no chocar con el tiempo de espera del
cliente:

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
- *«¿Quiénes reciben el apoyo más estrecho de sus colegas en las Constituyentes, y quién los apoya?»*:
  `connectedness`
- *«¿Hablan distinto en el pleno los diputados que articulan la red y los que se quedan en su
  partido?»*: `speech_by_network` y `distinctive_words`
- *«En los debates de la reforma agraria, ¿qué instituciones y conceptos aparecen juntos, y cuáles
  mencionan más las izquierdas que las derechas?»*: `library_create` y `cooccurrence_network`
- *«¿Quién nombra a quién en esos debates, y cuánto se nombran los grupos entre sí?»*: `mention_network`

## Herramientas

| grupo | herramientas |
|---|---|
| datos | `list_datasets` · `download_data` · `get_documentation` · `how_to_cite` · `describe_data` |
| discurso | `coverage` · `ngram_viewer` · `term_counter` · `term_frequency` · `share_of_voice` · `distinctive_words` · `kwic` · `collocations` · `search_text` · `get_intervention` · `get_session` |
| bibliotecas | `library_create` · `library_describe` · `library_edit` · `library_combine` · `library_rebuild` · `library_delete` · `library_export` · `library_import` |
| medidas | `search_measures` · `get_measure` |
| red | `coauthorship_network` (exporta GraphML o CSV para Gephi, igraph o R) · `deputy_neighbors` · `cross_group_coauthorship` |
| métricas | `network_metrics` · `structural_roles` (las publicadas, sin recalcular) · `connectedness` (Fowler 2006, calculada aquí desde las firmas; exporta CSV o GraphML) |
| discurso × red | `speech_by_network` · `deputy_profile` |
| redes sobre una biblioteca | `cooccurrence_network` (entidades mencionadas en la misma intervención) · `mention_network` (quién nombra a quién en el pleno). Escriben una página HTML interactiva, CSV, JSON y un resumen en la carpeta absoluta que se indique; el método está en el recurso `luz://methods/networks` |
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
- **`connectedness` sí se calcula aquí,** con la medida de Fowler (2006, *Political Analysis* 14: 456-487):
  cada cofirmante apoya al primer firmante con una fuerza de 1/(número de cofirmantes) por medida, la
  distancia es la inversa de esa fuerza y la puntuación es la inversa de la distancia media más corta
  desde el resto de la Cámara, una red por legislatura. El primer firmante hace de *sponsor*: su firma
  es siempre la del `id_dip_primer_autor`, el orden casi nunca es alfabético y defiende la medida en el
  85 % de las defendidas (Afinidades v3). Las firmas ilegibles y el «Siguen las firmas hasta N» cuentan en el número de
  cofirmantes. Como nadie es alcanzable desde todos los demás miembros, la puntuación lleva la
  corrección de Wasserman y Faust, que coincide con la de Fowler cuando el alcance es completo. Quien
  nunca firmó primero, o cuyas medidas nadie más firmó, no recibe apoyo y puntúa 0.
  `ties="undirected"` usa la ponderación de Newman (2001) entre todos los firmantes.
- **Algunas listas de firmas están truncadas en el Diario,** y a esas medidas les faltan aristas.
- **`mention_network` no puede separar homónimos por sexo,** porque no hay variable de sexo. Los separa
  por el nombre de pila o el partido escritos junto al apellido; lo que sigue siendo ambiguo se lista
  aparte y no se asigna. Las acotaciones del Diario entre paréntesis («(El Sr. X: …)») no cuentan.
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
codex mcp add luz -- uvx luz-mcp              # Codex CLI and the ChatGPT desktop app
uvx luz-mcp download                          # the data, once (about 210 MB, in ~/.luz)
```

**OpenCode** (`~/.config/opencode/opencode.json`, inside the `"mcp"` block):

```json
{ "mcp": { "luz": { "type": "local", "command": ["uvx", "luz-mcp"], "enabled": true } } }
```

**Antigravity, Claude Desktop, Cursor, Gemini CLI, Windsurf** and most other clients:

```json
{ "mcpServers": { "luz": { "command": "uvx", "args": ["luz-mcp"] } } }
```

Restart the client after changing its configuration. If a desktop app cannot start the server,
replace `"uvx"` with the full path printed by `which uvx`. ChatGPT on the web only accepts remote
servers.

The tools are listed in the table above. What to keep in mind:

- **There is no sex variable.**
- **Not all rows are speech.** `SUMARIO` and `COMENTARIOS` rows have `dm_speech = 0`.
- **There are two sets of party labels.** Compare voice with seats using the `reg_*` labels, those
  of the revised register.
- **The two datasets label the second legislature differently:** 1933-1935 and 1933-1936.
- **The network metrics are the published ones,** checked on import against the edge list.
- **`connectedness` is computed here,** with Fowler's (2006) measure: each co-signatory supports the
  first signatory with strength 1/(co-signatories) per measure, distance = 1/strength, one network per
  legislature, corrected for deputies who cannot reach one another (Wasserman and Faust; equal to
  Fowler's when reach is complete). The first signatory stands for the sponsor.
- **Some signature lists are truncated.**
- **The chair is left out of `speech_by_network` by default.** It signs no initiatives but speaks
  in every sitting.
- **Networks on a library:** `cooccurrence_network` (entities mentioned in the same intervention) and
  `mention_network` (who names whom). With no sex variable, `mention_network` tells namesakes apart by a
  given name or party written next to the surname, and lists the rest apart. Method: resource
  `luz://methods/networks`.
- **Libraries are written for the Luz y Taquígrafos explorer with the row numbers of version 3.**
  Import them there only with the version 3 CSV loaded.

luz-mcp is a profile of the [parlaibero-mcp](https://github.com/rodrodr/parlaibero-tools) engine.
The code is MIT-licensed; the data are CC BY 4.0. Cite each dataset with its version.
