# Changelog

## 0.3.0 · sin publicar

- `connectedness`: la medida de *legislative connectedness* de Fowler (2006, *Political Analysis* 14: 456-487),
  calculada desde las firmas de Afinidades, una red por legislatura. Fuerza del vínculo del cofirmante al
  primer firmante = Σ 1/cofirmantes de cada medida (con las firmas ilegibles y las declaradas en las listas
  truncadas); distancia = 1/fuerza; caminos mínimos (Dijkstra); inversa de la distancia media desde el resto
  de la Cámara, con la corrección de Wasserman y Faust para el alcance incompleto. Ranking, vínculos más
  fuertes, los apoyos más cercanos de un diputado, correlación con las centralidades publicadas y
  exportación a CSV o GraphML. Opción no dirigida con la ponderación de Newman (2001).

## 0.2.0 · 2026-10-14 · publicada en PyPI

Sobre el motor parlaibero-mcp 0.5.

- `cooccurrence_network` y `mention_network` sobre una biblioteca, con los grupos de esta colección
  (`party`, `party_family`, `ideology` y los `reg_*` del registro; por defecto `reg_family`). No hay variable
  de sexo, así que los homónimos se separan por el nombre de pila o el partido escritos junto al apellido.
- Recurso `luz://methods/networks` con el método.

## 0.1.0 · 2026-10-04

Primera versión (plan: `docs/PLAN_mcp.md`).

- Perfil de Luz y Taquígrafos V3 sobre el motor de parlaibero-mcp 0.4: las herramientas de discurso,
  bibliotecas y exportación, con `party_family`, `ideology` y las etiquetas del registro (`reg_*`).
- Tablas de Afinidades Elegidas 2.0 y nueve herramientas: medidas y firmas, red de coautorías,
  métricas y roles publicados, y discurso × red.
- Comprobaciones en cada carga: las cifras publicadas, los enlaces de las medidas al Diario (fecha y
  defensor) y el grado de cada diputado, recalculado desde la lista de aristas.
- Bibliotecas para el explorador de Luz con los números de fila de la V3, comprobadas contra su motor real.
