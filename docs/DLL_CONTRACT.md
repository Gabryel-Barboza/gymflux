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

$catraca = New-Object -ComObject "Henry.Kernel7x" # Nome do ProgID registrado
# Recuperando os métodos da variável
$catraca | Get-Member

Add_Acionamento               Method                void Add_Acionamento (int, SAcionamento)
Add_Feriado                   Method                void Add_Feriado (int, Date)
Add_FncEsp_Funcao             Method                void Add_FncEsp_Funcao (int, string, SFuncaoEx)
Add_FncEsp_Matricula          Method                void Add_FncEsp_Matricula (int, string)
Add_Funcao                    Method                void Add_Funcao (int, SFuncao)
Add_ItemAcesso                Method                void Add_ItemAcesso (int, SItemAcesso)
Add_Periodo                   Method                void Add_Periodo (int, SPeriodo)
BeginLargeTransfer            Method                void BeginLargeTransfer (int)
Bio_DropTemplate              Method                bool Bio_DropTemplate (string)
Bio_DropTemplates             Method                void Bio_DropTemplates ()
CancelarOperacao              Method                bool CancelarOperacao (int)
EndLargeTransfer              Method                void EndLargeTransfer (int)
PararColetaEventos            Method                bool PararColetaEventos (int)
RegistroOn                    Method                void RegistroOn (int, SRegistro)
RespostaOn                    Method                void RespostaOn (int, SResposta)
RespostaStatus                Method                void RespostaStatus (int, int)
SalvaImagemMemoria            Method                bool SalvaImagemMemoria (int, string)
SetConcentrador               Method                void SetConcentrador (int, bool)
SetConectado                  Method                void SetConectado (int, bool)
setConnResetTimeout           Method                void setConnResetTimeout (int, SResetCon)
SetICMPProtocol               Method                void SetICMPProtocol (int, bool)
SetorPercentualEx             Method                double SetorPercentualEx (SParticionamento, SParticao, SExpansao)
SetSearchTimeout              Method                void SetSearchTimeout (int)
SetSecurityLevel              Method                void SetSecurityLevel (byte)
SetSincronizar                Method                void SetSincronizar (int, bool)
Add_Escala                    ParameterizedProperty bool Add_Escala (int, SEscala, int) {get}
Add_Horario                   ParameterizedProperty bool Add_Horario (int, string, int) {get}
Add_MsgEspec                  ParameterizedProperty bool Add_MsgEspec (int, SMsgEspecifica) {get}
Add_UsuarioEquipamento        ParameterizedProperty bool Add_UsuarioEquipamento (int, SUsuarioEquipamento) {get}
AdicionaCard                  ParameterizedProperty bool AdicionaCard (SComConfig, int) {get}
AlterarVelocidade             ParameterizedProperty bool AlterarVelocidade (int, SVelocidade) {get}
ApagaUltimoPacote             ParameterizedProperty bool ApagaUltimoPacote (int) {get}
Bio_CarregaTemplate           ParameterizedProperty bool Bio_CarregaTemplate (string) {get}
Bio_CfgDefaultF_FL            ParameterizedProperty SDspcfg_F_FL Bio_CfgDefaultF_FL (SCfgDspPadrao) {get}
Bio_CriaDigitalM1M2           ParameterizedProperty bool Bio_CriaDigitalM1M2 (string, byte, bool, STemplate7x, STemp...
Bio_DelTemplate               ParameterizedProperty bool Bio_DelTemplate (int, string, bool) {get}
Bio_DelTemplateTodas          ParameterizedProperty bool Bio_DelTemplateTodas (int) {get}
Bio_EnvConfiguracaoF_FL       ParameterizedProperty bool Bio_EnvConfiguracaoF_FL (int, SDspcfg_F_FL) {get}
Bio_EnvConfiguracaoS          ParameterizedProperty bool Bio_EnvConfiguracaoS (int, SDspcfg_S) {get}
Bio_EnvTemplate               ParameterizedProperty bool Bio_EnvTemplate (int, string) {get}
Bio_GeraUserID                ParameterizedProperty string Bio_GeraUserID (SBiometria, string, byte, bool) {get}
Bio_GetMaxQuantLista          ParameterizedProperty bool Bio_GetMaxQuantLista (int, ushort) {get}
Bio_GetUsuario                ParameterizedProperty bool Bio_GetUsuario (int, SUsuarioBioEx) {get}
Bio_ProcuraTemplate           ParameterizedProperty string Bio_ProcuraTemplate (string, string) {get}
Bio_RecConfiguracaoF_FL       ParameterizedProperty bool Bio_RecConfiguracaoF_FL (int, SDspcfg_F_FL) {get}
Bio_RecConfiguracaoS          ParameterizedProperty bool Bio_RecConfiguracaoS (int, SDspcfg_S) {get}
Bio_RecListaUsuarios          ParameterizedProperty bool Bio_RecListaUsuarios (int) {get}
Bio_RecTemplate               ParameterizedProperty bool Bio_RecTemplate (int, string, string) {get}
Bio_RecUsuario                ParameterizedProperty bool Bio_RecUsuario (int, bool, SUsuarioBioEx) {get}
Bio_UsuarioExiste             ParameterizedProperty bool Bio_UsuarioExiste (int, string, bool) {get}
Bio_UsuariosQuant             ParameterizedProperty bool Bio_UsuariosQuant (int, ushort) {get}
Bio_UsuariosQuantLivre        ParameterizedProperty bool Bio_UsuariosQuantLivre (int, ushort) {get}
ColetaEventos                 ParameterizedProperty bool ColetaEventos (int, string) {get}
ColetaEventosEx               ParameterizedProperty bool ColetaEventosEx (int, string, Date, SEmpregador) {get}
DataHoraUltimaComunicacao     ParameterizedProperty bool DataHoraUltimaComunicacao (int, double) {get}
DetectarVelocidade            ParameterizedProperty bool DetectarVelocidade (int, SVelocidade) {get}
DigitosRange                  ParameterizedProperty int DigitosRange (SPlacaCard, bool) {get}
EnviaAcionaCtrl               ParameterizedProperty bool EnviaAcionaCtrl (int, byte, SAcionaCtrl) {get}
EnviaAcionamentos             ParameterizedProperty bool EnviaAcionamentos (int) {get}
EnviaBeep                     ParameterizedProperty bool EnviaBeep (int, SBeep) {get}
EnviaCfgControlador           ParameterizedProperty bool EnviaCfgControlador (int, byte, SConfigCtrl) {get}
EnviaConfiguracao             ParameterizedProperty bool EnviaConfiguracao (int, SConfiguracao) {get}
EnviaDadosEmpregador          ParameterizedProperty bool EnviaDadosEmpregador (int, SEmpregador) {get}
EnviaDataHora                 ParameterizedProperty bool EnviaDataHora (int, Date) {get}
EnviaDataHoraEx               ParameterizedProperty bool EnviaDataHoraEx (int, SDataHoraCompleta) {get}
EnviaFacilityCodes            ParameterizedProperty bool EnviaFacilityCodes (int, byte, SFacility) {get}
EnviaFeriados                 ParameterizedProperty bool EnviaFeriados (int) {get}
EnviaFuncoes                  ParameterizedProperty bool EnviaFuncoes (int) {get}
EnviaHorarios                 ParameterizedProperty bool EnviaHorarios (int) {get}
EnviaListaAcesso              ParameterizedProperty bool EnviaListaAcesso (int) {get}
EnviaListaAcessoThd           ParameterizedProperty bool EnviaListaAcessoThd (int) {get}
EnviaListaUsuarios            ParameterizedProperty bool EnviaListaUsuarios (int) {get}
EnviaMsgPadrao                ParameterizedProperty bool EnviaMsgPadrao (int, SMsgPadrao) {get}
EnviaMsgsEspecificas          ParameterizedProperty bool EnviaMsgsEspecificas (int) {get}
EnviaParticionamento          ParameterizedProperty bool EnviaParticionamento (int, SParticionamento) {get}
EnviaPeriodos                 ParameterizedProperty bool EnviaPeriodos (int) {get}
EnviaTipoCatraca              ParameterizedProperty bool EnviaTipoCatraca (int, SOperacaoCatraca) {get}
EnviaUsuarioEquipamento       ParameterizedProperty bool EnviaUsuarioEquipamento (int, SUsuarioEquipamento) {get}
ErrorDescription              ParameterizedProperty string ErrorDescription (int) {get}
ExistemRegistros              ParameterizedProperty bool ExistemRegistros (int, bool) {get}
ExportConfiguracao            ParameterizedProperty bool ExportConfiguracao (string, SConfiguracao) {get}
getConnResetTimeout           ParameterizedProperty bool getConnResetTimeout (int, SResetCon) {get}
ImportConfiguracao            ParameterizedProperty bool ImportConfiguracao (string, SConfiguracao) {get}
MostRecentFirmware            ParameterizedProperty string MostRecentFirmware (SConfiguracao) {get}
NumDigitosPadraoT             ParameterizedProperty byte NumDigitosPadraoT (SConfiguracao) {get}
NumDigitosValidos             ParameterizedProperty byte NumDigitosValidos (SConfiguracao) {get}
OpenTemplate7x                ParameterizedProperty bool OpenTemplate7x (string, STemplate7x) {get}
QuantRegsColetados            ParameterizedProperty int QuantRegsColetados (int) {get}
RecebeAcionamentos            ParameterizedProperty bool RecebeAcionamentos (int) {get}
RecebeCfgControlador          ParameterizedProperty bool RecebeCfgControlador (int, byte, SConfigCtrl) {get}
RecebeConfiguracao            ParameterizedProperty bool RecebeConfiguracao (int, SConfiguracao) {get}
RecebeDadosEmpregador         ParameterizedProperty bool RecebeDadosEmpregador (int, SEmpregador) {get}
RecebeDataHora                ParameterizedProperty bool RecebeDataHora (int, Date) {get}
RecebeDataHoraEx              ParameterizedProperty bool RecebeDataHoraEx (int, SDataHoraCompleta) {get}
RecebeFacilityCodes           ParameterizedProperty bool RecebeFacilityCodes (int, byte, SFacility) {get}
RecebeFeriados                ParameterizedProperty bool RecebeFeriados (int) {get}
RecebeFuncoes                 ParameterizedProperty bool RecebeFuncoes (int) {get}
RecebeHorarios                ParameterizedProperty bool RecebeHorarios (int) {get}
RecebeListaAcesso             ParameterizedProperty bool RecebeListaAcesso (int) {get}
RecebeListaUsuarioEquipamento ParameterizedProperty bool RecebeListaUsuarioEquipamento (int) {get}
RecebeMsgPadrao               ParameterizedProperty bool RecebeMsgPadrao (int, SMsgPadrao) {get}
RecebeMsgsEspecificas         ParameterizedProperty bool RecebeMsgsEspecificas (int) {get}
RecebePacote                  ParameterizedProperty bool RecebePacote (int) {get}
RecebeParticionamento         ParameterizedProperty bool RecebeParticionamento (int, SParticionamento) {get}
RecebePeriodos                ParameterizedProperty bool RecebePeriodos (int) {get}
RecebeQtRegistros             ParameterizedProperty bool RecebeQtRegistros (int, int) {get}
RecebeTipoCatraca             ParameterizedProperty bool RecebeTipoCatraca (int, SOperacaoCatraca) {get}
RecuperaRegistros             ParameterizedProperty bool RecuperaRegistros (int) {get}
Rec_Acionamento               ParameterizedProperty bool Rec_Acionamento (int, SAcionamento) {get}
Rec_Escala                    ParameterizedProperty bool Rec_Escala (int, SEscala) {get}
Rec_Feriado                   ParameterizedProperty bool Rec_Feriado (int, Date) {get}
Rec_FncEsp_Funcao             ParameterizedProperty bool Rec_FncEsp_Funcao (int, string, SFuncaoEx) {get}
Rec_FncEsp_Matricula          ParameterizedProperty bool Rec_FncEsp_Matricula (int, string) {get}
Rec_Funcao                    ParameterizedProperty bool Rec_Funcao (int, SFuncao) {get}
Rec_Horario                   ParameterizedProperty bool Rec_Horario (int, string) {get}
Rec_ItemAcesso                ParameterizedProperty bool Rec_ItemAcesso (int, SItemAcesso) {get}
Rec_MsgEspec                  ParameterizedProperty bool Rec_MsgEspec (int, SMsgEspecifica) {get}
Rec_Periodo                   ParameterizedProperty bool Rec_Periodo (int, SPeriodo) {get}
Rec_UsuarioEquipamento        ParameterizedProperty bool Rec_UsuarioEquipamento (int, SUsuarioEquipamento) {get}
RegistroOff                   ParameterizedProperty bool RegistroOff (int, SRegistro) {get}
RemoveCard                    ParameterizedProperty bool RemoveCard (int) {get}
SaveAsTemplate7x              ParameterizedProperty bool SaveAsTemplate7x (string, STemplate7x) {get}
Set485OffNumber               ParameterizedProperty bool Set485OffNumber (int, byte) {get}
SetorPercentual               ParameterizedProperty double SetorPercentual (SParticionamento, SParticao) {get}
SRAcionamentos                ParameterizedProperty int SRAcionamentos (SConfiguracao, int) {get}
SRFeriados                    ParameterizedProperty int SRFeriados (SConfiguracao, int) {get}
SRFuncoes                     ParameterizedProperty int SRFuncoes (SConfiguracao, int) {get}
SRFuncoesEspecificas          ParameterizedProperty int SRFuncoesEspecificas (SConfiguracao, int, int) {get}
SRHorariosEscalas             ParameterizedProperty int SRHorariosEscalas (SConfiguracao, int, int, int, int) {get}
SRListaAcesso                 ParameterizedProperty int SRListaAcesso (SConfiguracao, int) {get}
SRMsgEspecifica               ParameterizedProperty int SRMsgEspecifica (SConfiguracao, int, int) {get}
SRPeriodos                    ParameterizedProperty int SRPeriodos (SConfiguracao, int) {get}
TamanhoItemAcesso             ParameterizedProperty int TamanhoItemAcesso (SConfiguracao) {get}
TamanhoRegistro               ParameterizedProperty int TamanhoRegistro (SConfiguracao) {get}
ThreadLastError               ParameterizedProperty int ThreadLastError (int) {get}
ThreadPrioridade              ParameterizedProperty int ThreadPrioridade (SPrioridade) {set}
USB_EnviaCartucho             ParameterizedProperty bool USB_EnviaCartucho (int, string) {get}
USB_RecebeCartucho            ParameterizedProperty bool USB_RecebeCartucho (int, string) {get}
KernelLastError               Property              int KernelLastError () {get}
ListaPortasSeriais            Property              string ListaPortasSeriais () {get}
MoreRecentFirmware            Property              string MoreRecentFirmware () {get}
RaiseExceptions               Property              bool RaiseExceptions () {get} {set}
USB_Remove                    Property              bool USB_Remove () {get}
Versao                        Property              string Versao () {get}
```

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
