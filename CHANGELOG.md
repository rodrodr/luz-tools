# Changelog

## Sin publicar

- `transpartisan_cosigning`: cada medida es unipartidista, bipartidista o multipartidista según el número
  efectivo de partidos (NEP, Laakso y Taagepera 1979) de sus firmantes: < 1,5, de 1,5 a < 2,5, ≥ 2,5. Sustituye
  al umbral de cuota de cofirmantes de otros partidos (`threshold`), tomado de un marco bipartidista que no
  encaja en una cámara de muchos partidos. Nuevos campos: `coalitions` y `mean_nep` por legislatura, tipo y
  tema; `signed_uni/bi/multi`, `mean_nep_signed` y `mean_nep_first_signed` por diputado.
- `homophily`: díadas, pruebas QAP y logit solo entre los diputados que firmaron alguna de las medidas
  (`deputies_who_signed`). Los que no firmaron ninguna aportaban ceros estructurales y, en 1936-1939 (181 de
  501), separaban el logit. Sus coeficientes coinciden ahora con los de R hasta 0,00005.
- `analysis/inferencia_redes/`: la homofilia y los roles de intermediación, comprobados con MRQAP, ERGM de dos
  modos y permutaciones (informe en `INFORME.md`). El sdist excluye `analysis`.
- `CITATION.cff` en 0.3.0; el sdist excluye `.claude` y los `.DS_Store`; `.gitignore` los ignora.

## 0.3.0 · 2026-10-18 · publicada en PyPI

- `connectedness`: la medida de *legislative connectedness* de Fowler (2006, *Political Analysis* 14: 456-487),
  calculada desde las firmas de Afinidades, una red por legislatura. Fuerza del vínculo del cofirmante al
  primer firmante = Σ 1/cofirmantes de cada medida (con las firmas ilegibles y las declaradas en las listas
  truncadas); distancia = 1/fuerza; caminos mínimos (Dijkstra); inversa de la distancia media desde el resto
  de la Cámara, con la corrección de Wasserman y Faust para el alcance incompleto. Ranking, vínculos más
  fuertes, los apoyos más cercanos de un diputado, correlación con las centralidades publicadas y
  exportación a CSV o GraphML. Opción no dirigida con la ponderación de Newman (2001).
- Cinco medidas de grupos en la red, calculadas desde las firmas, una red por legislatura, con los grupos del
  registro (partido, familia, ideología, distrito o región histórica):
  - `brokerage_roles`: roles de intermediación de Gould y Fernandez (1989) en la red de apoyo (coordinador,
    consultor, representante, guardián, enlace), con valores esperados y z de su modelo nulo. Recuentos,
    esperados y z comprobados contra `sna::brokerage` de R.
  - `transpartisan_cosigning`: cofirma entre grupos como indicador diádico agregado al diputado y a la cámara
    (en la línea de Harbridge 2015), más la coalición de cada medida. Reproduce 1 − `party_frac_partido`.
  - `homophily`: probabilidad de vínculo condicionada a compartir atributos, con QAP y logit diádico con
    efectos fijos de actividad; exporta las díadas para un ERGM.
  - `block_density`: densidades intra- e interbloque, imagen al umbral de la densidad global (Alemán y Calvo 2013).
  - `assortativity`: asortatividad nominal de Newman (2003) con error típico jackknife, y la escalar de la ideología.

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
