# lint-fix

Ejecuta ruff (igual que el CI) y repara automáticamente los errores encontrados.

## Pasos

1. Verificar que ruff esté disponible; si no, instalarlo desde `requirements-dev.txt`:
   ```
   pip install -r requirements-dev.txt
   ```

2. Ejecutar `ruff check . --fix` para corregir errores de linting automáticamente.

3. Ejecutar `ruff format .` para aplicar el formato (equivalente a pasar `ruff format --check .` en CI).

4. Volver a ejecutar `ruff check .` (sin `--fix`) para mostrar los errores que quedaron y que requieren intervención manual.

5. Reportar al usuario:
   - Cuántos errores se corrigieron automáticamente.
   - Qué archivos fueron reformateados.
   - Si quedan errores manuales, mostrarlos con su ubicación y explicar cómo resolverlos.

## Comandos exactos del CI

```bash
# Lo que corre el CI (sólo verifica, no repara):
ruff check .
ruff format --check .

# Lo que esta skill ejecuta (verifica Y repara):
ruff check . --fix
ruff format .
ruff check .   # segunda pasada para mostrar errores residuales
```

## Notas

- La versión fijada en CI es `ruff==0.4.4` (definida en `requirements-dev.txt`).
- Los tests (`pytest`) corren después del lint en CI; esta skill sólo cubre lint.
- Si hay errores que ruff no puede corregir solo (p.ej. imports no usados que son parte de la lógica), indícalos al usuario con el número de línea y la regla ruff correspondiente.
