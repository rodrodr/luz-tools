# Inferencia en la red de cofirmas de la Segunda República

¿Son reales la homofilia y los roles de intermediación que miden las herramientas `homophily` y
`brokerage_roles` de luz-mcp, o los produce la dependencia entre vínculos de una red?

19 de octubre de 2026. Afinidades Elegidas (Dataverse, versión 2.0); luz-mcp 0.3.0 con el cambio de
`transpartisan_cosigning` pendiente de revisión, que no afecta a estas medidas; R 4.5.2, `sna` 2.8,
`ergm` 4.12.0, `network` 1.19.0.

## En resumen

- **La homofilia es real.** Compartir partido, familia, distrito o región, y la cercanía ideológica,
  aumentan la probabilidad de cofirmar en las tres legislaturas. Lo sostienen las tres pruebas que
  tienen en cuenta la dependencia entre vínculos: MRQAP, ERGM de dos modos y, en 1936-1939, ERGM de
  dos modos con colaboración repetida.
- **Una excepción: misma familia en 1936-1939.** El logit ingenuo la da negativa y significativa
  (−0,19, p = 0,003). Con MRQAP deja de serlo (p = 0,06), y con el ERGM de dos modos cambia de signo y
  tampoco es significativa (+0,14, p = 0,32). En esa legislatura, compartir familia no añade nada a
  compartir partido, distrito, región e ideología.
- **Los roles de intermediación también son reales.** Con la red fija y las etiquetas barajadas, hay
  más coordinación, representación y guardia de lo que daría el azar, y menos consultoría y enlace,
  igual que con los z de Gould y Fernandez. En 1936-1939 el patrón se debilita en consultor y guardián.
- **Corregido en la herramienta.** El logit de `homophily` incluía a los diputados que no firmaron
  nada. Sus díadas son ceros estructurales, y en 1936-1939 (181 de 501 miembros) eso separaba el modelo
  por completo: los coeficientes de actividad divergían. Ahora `homophily` usa solo a quienes firmaron al
  menos una medida (`deputies_who_signed`), como este análisis, y sus coeficientes coinciden con los de
  R hasta 0,00005 en las tres legislaturas, sin separación. Sus errores típicos siguen siendo ingenuos:
  para inferencia, `qap_p` o un modelo de red.

## Datos y especificación

Una red no dirigida por legislatura: dos diputados están vinculados si firmaron al menos una medida
juntos. Es la lista de aristas publicada por Afinidades, reconstruida desde las firmas por luz-mcp
(`00_export.py`).

El conjunto de riesgo son los miembros que firmaron al menos una medida. Un diputado que no firmó
nada no puede tener vínculos: incluirlo añade ceros que no informan de nada y, en 1936-1939, hace
inestimable el logit.

| legislatura | diputados con alguna firma | díadas | vínculos |
|---|---|---|---|
| 1931-1933 | 454 | 102.831 | 16.361 |
| 1933-1936 | 442 | 97.461 | 15.119 |
| 1936-1939 | 320 | 51.040 | 5.220 |

Covariables, como en `homophily`: mismo partido, misma familia, mismo distrito, misma región histórica
y distancia ideológica (EI = 0 … ED = 6). El partido está anidado en la familia y el distrito en la
región, así que cada coeficiente es el incremento sobre el más amplio. La actividad de los dos
diputados (medidas firmadas, en terciles cortados por valor) entra como efectos fijos.

No hay variables de género, raza ni comisión.

## Métodos

1. **Logit diádico** (`01_logit.R`). Reproduce el de la herramienta: los coeficientes coinciden hasta
   0,00005 en las tres legislaturas. Con la corrección de `homophily`, la especificación de la
   herramienta y la del análisis (el conjunto de riesgo) son la misma. Sus p suponen díadas
   independientes.
2. **MRQAP** (`02_mrqap.R`, `sna::netlogit`). Mismos coeficientes que el logit; el p sale de 1.000
   permutaciones con el doble semiparcialeo de Dekker (`qapspp`), adecuado para covariables correlacionadas
   como partido y familia. Se hicieron en 4 bloques de 250 con semillas distintas, reunidos en
   `04_combine.py`.
3. **ERGM de una capa** (`03_ergm.R`). La versión de díadas independientes (MPLE) reproduce el logit. La
   que añade cierre triádico (`gwesp`, decaimiento 0,5) **no converge**: tras 11–25 iteraciones los pasos
   seguían entre 0,05 y 0,13 (`results/ergm_gwesp_stopped.txt`). Es lo esperable en una red proyectada,
   donde cada medida une a todos sus firmantes entre sí. Sus estimaciones no se usan.
4. **ERGM de dos modos** (`06_ergm_bipartite.R`). Diputados × medidas, un vínculo por firma
   identificada; solo medidas con al menos dos firmantes identificados. Es como se generan los datos.
   - Homofilia: `b1nodematch` (Bomiriya et al. 2023, con descuento β = 0,5) para partido, familia,
     distrito, región e ideología. No hay término de distancia, por eso el modelo usa misma ideología.
   - Se fijan las dos secuencias de grado (`constraints = ~ degrees`): cada diputado conserva cuántas
     medidas firmó y cada medida cuántos firmantes tiene. La actividad y el tamaño de las medidas
     quedan controlados exactamente; solo varía quién firma con quién.
   - Converge en las tres legislaturas con un 99 % de confianza, y las simulaciones reproducen los
     estadísticos observados (p de Monte Carlo entre 0,26 y 0,98).
   - Pero deja pocas parejas que firman muchas medidas juntas: la colaboración se concentra en parejas
     estables más de lo que explica la homofilia.
5. **ERGM de dos modos con colaboración repetida.** Añade `gwb1dsp` (decaimiento 0,5). Converge en
   1936-1939 y mejora el ajuste a esa distribución. En 1931-1933 y 1933-1936 iba a unos 15–20 minutos por
   iteración y no habría convergido dentro del tope de 40; se paró en la iteración 4
   (`results/ergm_dsp_stopped.txt`).
6. **Roles de intermediación** (`05_brokerage_perm.py`). Los z de Gould y Fernandez comparan con una red
   aleatoria de la misma densidad, que no conserva el grado de nadie. Aquí la red se deja como es y se
   barajan las etiquetas de partido o familia entre los miembros, 2.000 veces.

Los coeficientes del logit y del ERGM de dos modos no están en la misma escala: el logit da log-odds de
un vínculo, y el ERGM el efecto sobre los dos-caminos que comparten atributo. Se comparan signo y
significación, no tamaño.

## Homofilia

**1931-1933**

| covariable | logit: coef. | logit: p ingenuo | MRQAP: p | ERGM 2 modos: coef. | p |
|---|---|---|---|---|---|
| mismo partido | +0,78 | < 0,001 | < 0,001 | +0,68 | < 0,001 |
| misma familia | +0,40 | < 0,001 | < 0,001 | +0,51 | < 0,001 |
| mismo distrito | +0,88 | < 0,001 | < 0,001 | +0,75 | < 0,001 |
| misma región | +0,75 | < 0,001 | < 0,001 | +0,79 | < 0,001 |
| distancia ideológica | −0,43 | < 0,001 | < 0,001 | — | — |
| misma ideología | — | — | — | +0,39 | < 0,001 |

**1933-1936**

| covariable | logit: coef. | logit: p ingenuo | MRQAP: p | ERGM 2 modos: coef. | p |
|---|---|---|---|---|---|
| mismo partido | +0,68 | < 0,001 | < 0,001 | +0,57 | < 0,001 |
| misma familia | +0,31 | < 0,001 | < 0,001 | +0,43 | < 0,001 |
| mismo distrito | +1,51 | < 0,001 | < 0,001 | +1,30 | < 0,001 |
| misma región | +0,56 | < 0,001 | < 0,001 | +0,55 | < 0,001 |
| distancia ideológica | −0,57 | < 0,001 | < 0,001 | — | — |
| misma ideología | — | — | — | +0,87 | < 0,001 |

**1936-1939**

| covariable | logit: coef. | logit: p ingenuo | MRQAP: p | ERGM 2 modos: coef. | p | + colab. repetida: coef. | p |
|---|---|---|---|---|---|---|---|
| mismo partido | +0,62 | < 0,001 | < 0,001 | +0,76 | < 0,001 | +0,80 | < 0,001 |
| misma familia | −0,19 | 0,003 | 0,060 | +0,14 | 0,318 | +0,07 | 0,600 |
| mismo distrito | +0,47 | < 0,001 | < 0,001 | +1,00 | < 0,001 | +0,99 | < 0,001 |
| misma región | +0,34 | < 0,001 | < 0,001 | +0,29 | 0,005 | +0,28 | 0,005 |
| distancia ideológica | −0,85 | < 0,001 | < 0,001 | — | — | — | — |
| misma ideología | — | — | — | +0,67 | < 0,001 | +0,64 | < 0,001 |

«< 0,001» en el MRQAP quiere decir que ninguna de las 1.000 permutaciones alcanzó el valor observado.

Lo que se lee:
- **Partido, distrito, región e ideología** son robustos en las tres legislaturas.
- **El distrito pesa mucho**, sobre todo en 1933-1936. Las circunscripciones eran plurinominales y
  provinciales, y los diputados de una misma provincia firmaban juntos más allá del partido.
- **La familia** suma al partido en las dos primeras legislaturas. En 1936-1939 no.
- **1936-1939 es la legislatura más débil:** 89 medidas útiles, 320 diputados con alguna firma y una
  red mucho menos densa.

## Roles de intermediación

Cociente entre el total observado de cada rol y su media con las etiquetas barajadas (red fija, 2.000
permutaciones). Mayor que 1 = más que el azar. Sin marca, p < 0,01 en la dirección del cociente.

| legislatura | grupos | coordinador | consultor | representante | guardián | enlace |
|---|---|---|---|---|---|---|
| 1931-1933 | partido | 4,86 | 0,53 | 2,16 | 1,91 | 0,63 |
| 1931-1933 | familia | 5,78 | 0,47 | 1,74 | 1,74 | 0,44 |
| 1933-1936 | partido | 8,63 | 0,54 | 2,39 | 2,09 | 0,47 |
| 1933-1936 | familia | 6,04 | 0,55 | 2,03 | 1,70 | 0,43 |
| 1936-1939 | partido | 5,31 | 0,85 (n.s.) | 2,25 | 2,00 (p < 0,05) | 0,55 |
| 1936-1939 | familia | 6,44 | 0,73 (p < 0,05) | 1,76 | 1,69 (p < 0,05) | 0,40 |

El apoyo fluye sobre todo dentro de los grupos (coordinación) y entre un grupo y otro a través de un
miembro de uno de los dos (representante y guardián). Es raro que pase por un tercero ajeno (consultor
y enlace). Es el mismo orden que dan los z de Gould y Fernandez, ahora con el grado de cada diputado
fijo. El desglose por grupo está en `results/brokerage_perm_groups.csv`.

## Límites

- La comprobación con colaboración repetida solo terminó en 1936-1939.
- El ERGM de dos modos no tiene un término de distancia ideológica: usa misma ideología (una de las
  siete posiciones).
- Las firmas ilegibles y las listas truncadas faltan en la red, como en todas las herramientas.
- No hay género, raza ni comisión.

## Reproducir

Desde la raíz del repositorio, con los datos de luz-mcp descargados:

```
.venv/bin/python analysis/inferencia_redes/00_export.py
Rscript analysis/inferencia_redes/01_logit.R
Rscript analysis/inferencia_redes/02_mrqap.R <legislatura> 250 <semilla>     # semillas 1-4 por legislatura
Rscript analysis/inferencia_redes/03_ergm.R <legislatura> indep
Rscript analysis/inferencia_redes/06_ergm_bipartite.R <legislatura> 0.5 1     # añadir 'dsp' para gwb1dsp
.venv/bin/python analysis/inferencia_redes/05_brokerage_perm.py 2000
python3 analysis/inferencia_redes/04_combine.py
```

Los datos exportados (`data/`) y los objetos de R (`*.rds`) no se guardan en git; se regeneran con los
scripts. Los resultados en CSV, los diagnósticos MCMC y los GOF en PDF están en `results/`.

## Referencias

- Bomiriya, R. P., Bansal, S., & Hunter, D. R. (2023). Modeling Homophily in Exponential-Family Random
  Graph Models for Bipartite Networks. arXiv:2312.05673. https://arxiv.org/abs/2312.05673
- Dekker, D., Krackhardt, D., & Snijders, T. A. B. (2007). Sensitivity of MRQAP Tests to Collinearity and
  Autocorrelation Conditions. *Psychometrika* 72(4): 563-581. doi:10.1007/s11336-007-9016-1
- Gould, R. V., & Fernandez, R. M. (1989). Structures of Mediation. *Sociological Methodology* 19: 89-126.
  doi:10.2307/270949
