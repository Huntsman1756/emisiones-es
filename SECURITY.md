# Política de seguridad

## Alcance

Emisiones ES es un proyecto de investigación/datos. La superficie de riesgo
principal es la **reviewer app de P0** (`p0/app/`): un servidor HTTP local
para revisión humana de términos contractuales.

Defensas implementadas (verificadas por `tests/test_p0_http.py`):

- escucha solo en loopback; Host/Origin/Sec-Fetch-Site restringidos a
  same-origin (sin cookies ni credenciales);
- autorización por caso/documento server-side (la sesión asignada decide
  modo MANUAL/ASSISTED y documentos visibles);
- límites de tamaño/página/escala en render PDF; serialización de acceso a
  pypdfium2; caché acotada;
- JSON estricto (sin claves duplicadas, sin NaN/Infinity, profundidad y
  cardinalidad limitadas);
- logs JSONL append-only con fsync y escritura atómica de sesión;
- CSP estricta, `nosniff`, `X-Frame-Options: DENY`, CORP same-origin.

La app **no** está pensada para exponerse a red. No la sirvas detrás de un
proxy ni la abras fuera de loopback.

## Datos y privacidad

El repositorio no distribuye documentos fuente ni texto completo derivado
(ver `docs/licensing.md`). Si encuentras un documento fuente, credencial o
dato personal commiteado, repórtalo como se indica abajo.

## Reportar una vulnerabilidad

Abre un *security advisory* privado en GitHub
(Repository → Security → Advisories) o contacta al maintainer por el canal
indicado en su perfil. **No abras un issue público** para vulnerabilidades
no publicadas. Se agradece incluir: descripción, impacto, pasos de
reproducción y versión/commit afectado.

No hay SLA formal: proyecto mantenido por voluntarios.
