# Contrato Henry 7x — kernel7x.dll

> **Objetivo:** documentar fielmente o contrato exposto por `kernel7x.dll` para gerar `src/gms_app/hardware/henry7x/real.py`.
> **Fonte:** inspeção via `pefile` + PowerShell + manuais Henry. **Não** distribuir a DLL neste repo.

## 1. Metadados da DLL

| Campo | Valor (preencher após inspeção) |
|-------|---------------------------------|
| Arquivo | `kernel7x.dll` |
| Arquitetura | 32-bit (PE32, `IMAGE_FILE_MACHINE_I386`) ✅ confirmado pelo dono |
| Compilador | _preencher: MSVC / Delphi? (pefile `VS_VERSIONINFO`)_ |
| Versão | _preencher: FileVersion em propriedades_ |
| Tamanho | _preencher: bytes_ |
| SHA256 | _preencher: `sha256sum vendor/kernel7x.dll`_ |
| Modelo catraca | _preencher: 7x / 7x Plus / Biométrica / QR?_ |
| SDK/Manual | _preencher: pasta `Exemplo VB6/C#/Delphi` entregue?_ |
| Dependências | _preencher: `kernel7x.dll` depende de `msvcr*.dll`, `sqlite` etc? (`ldd`/`dumpbin /dependents`)_ |

## 2. Como Extrair o Contrato (você, dono)

### 2.1 Você já fez (PowerShell)

Cole aqui o output que você extraiu via PowerShell (lista de exports + assinaturas). Use bloco de código:

```powershell
# Exemplo do que você rodou — mantenha o comando exato que usou
# Dump do seu ambiente:
```

> **COLE SEU DUMP ABAIXO (substitua este parágrafo):**
>
> ```
> (cole aqui as 30-200 linhas do PowerShell — ex: Get-ExportedFunction, [DllImport] etc)
> ```

### 2.2 Linux (dev) — automatizado

```bash
# Já deixamos pronto:
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
uv run python scripts/inspect_dll.py --dump vendor/kernel7x.dll --output dumps/kernel7x.txt

# Fallbacks manuais:
strings vendor/kernel7x.dll | grep -i -E "conectar|liberar|bloquear|henry" | head -n 100
python3 -c "import pefile; pe=pefile.PE('vendor/kernel7x.dll'); print([e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols])"
```

### 2.3 Windows (prod) — recomendado

```powershell
# Visual Studio dumpbin (Developer Command Prompt):
dumpbin /exports kernel7x.dll
dumpbin /headers kernel7x.dll | Select-String -Pattern "machine|dll characteristics"
dumpbin /dependents kernel7x.dll

# Alternativas GUI: Dependencies.exe (lucasg/Dependencies), PE-Bear, CFF Explorer

# Se vier .h / .tlb / .pas:
# Cole o trecho do header com as assinaturas (ex: kernel7x.h)
```

## 3. Tabela de Funções (preencher)

> Cada linha = 1 export da DLL. Descobrimos via `dumpbin /exports` ou `pefile`. Exemplo ilustrativo — **substitua pelos reais**.

| # | Export (nome mangled) | Nome amigável | Assinatura (C/Python ctypes) | Convenção | Retorno / Erros | Descrição |
|---|-----------------------|---------------|------------------------------|-----------|-----------------|-----------|
| 1 | `_Conecta@8` | `Conecta` | `int Conecta(int porta, int baud)` → `WinDLL.Conecta(c_int, c_int) -> c_int (0=ok)` | stdcall | 0=ok, <0=erro | Abre porta serial/TCP da catraca |
| 2 | `_Desconecta@0` | `Desconecta` | `void Desconecta()` | stdcall | — | Fecha conexão |
| 3 | `_LiberaCatraca@4` | `LiberaCatraca` | `int LiberaCatraca(int direcao)` | stdcall | 0=ok | Libera giro (1=entrada, 2=saída) |
| 4 | ... | ... | ... | ... | ... | ... |

**Campos para cada função:**
- **Convenção:** `stdcall` (`WinDLL`) vs `cdecl` (`CDLL`) — Henry tipicamente usa `stdcall` (WinAPI). Confirmar via header (`WINAPI`, `__stdcall`).
- **Tipos:** mapear para `ctypes` (`c_int`, `c_char_p`, `c_wchar_p`, `POINTER`, `create_string_buffer`).
- **Erros:** códigos de retorno, `GetLastError`, ou buffer de mensagem?

### 3.1 Callbacks / Eventos

Henry frequentemente usa polling ou callback registrado:

- Polling: `int ConsultaEvento(char* buffer, int size)` chamado em loop?
- Callback: `void RegistraCallback(void (*cb)(int evento, void* dados))`?

Documente aqui o mecanismo real.

## 4. Fluxo Típico (inferido, confirmar)

```
1. Conecta(porta=1 / ip="192.168.0.100", baud=9600) -> 0
2. ConfiguraCatraca(...) ?
3. Loop:
     AguardaIdentificacao() -> retorna cartao/biometria/teclado
     -> services.LiberarAcessoService.decide()
     -> if permitido: LiberaCatraca(ENTRADA) else: NegaAcesso(motivo)
     -> AguardaGiro(timeout=7000) -> LIBERADO / TIMEOUT / BLOQUEADO
4. Desconecta()
```

## 5. Mapeamento para `hardware/henry7x/interface.py`

| Método interface | Export DLL candidato | Notas |
|-----------------|----------------------|-------|
| `conectar(porta)` | `Conecta` / `Inicializa` / `Open` | |
| `desconectar()` | `Desconecta` / `Close` | |
| `liberar(direcao)` | `LiberaCatraca` / `LiberaAcesso` | dir 1/2 ou enum? |
| `bloquear()` | `BloqueiaCatraca` / `Bloqueia` | |
| `on_giro(cb)` | `CallbackGiro` / polling `StatusGiro` | |
| `status()` | `Status` / `Versao` / `LeContador` | |

## 6. Perguntas para Preencher `real.py`

- [ ] Lista completa de exports (cole `dumpbin /exports`).
- [ ] Headers `.h` / `.pas` / `.cs` com assinaturas (se existirem em `Exemplos/`).
- [ ] A DLL espera `char*` ANSI ou `wchar_t*` Unicode? (testar com `c_char_p` vs `c_wchar_p`).
- [ ] Como autentica a catraca? Precisa de `InicializaDll` com serial/license?
- [ ] Comunicação é serial (COM1), TCP/IP ou USB? Porta configurável?
- [ ] Há `kernel7x.ini` ou .cfg associado?

## 7. Próximos Passos Técnicos

1. Você cola o dump PowerShell na seção 2.1.
2. Rodamos `scripts/inspect_dll.py` localmente (se enviar a DLL via `vendor/` — não versionada) para cruzar exports.
3. Preenchemos a tabela §3 e geramos `src/gms_app/hardware/henry7x/real.py` esqueleto com `ctypes.WinDLL` + `argtypes`/`restype`.
4. Testamos em VM Windows 32-bit com catraca real.

---
*Template criado em 2026-09-11. Mantenha este arquivo como fonte de verdade do contrato.*
