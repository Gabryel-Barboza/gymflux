# vendor — DLLs Henry (NÃO versionar binários)

Coloque aqui localmente (não commitado — *.dll está no .gitignore):
- kernel7x.dll (32-bit)
- demais DLLs/exemplos Henry

Para inspecionar:
```bash
uv run python scripts/inspect_dll.py vendor/kernel7x.dll --dump --output dumps/kernel7x.txt
```

O conteúdo de `vendor/` é ignorado pelo git. Só este README é versionado via `!vendor/README.md`? Na verdade .gitignore ignora *.dll mas não o diretório — ajuste se necessário.
