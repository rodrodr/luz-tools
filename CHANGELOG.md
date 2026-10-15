# Changelog

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
