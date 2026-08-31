# Agua Viva 2

Aplicacao Flask para registro de qualidade da agua com interface inspirada no projeto original `aguaviva`.

Nesta versao, o salvamento nao usa SQL nem API propria: ao clicar em **Salvar**, os dados sao enviados diretamente para o endpoint `formResponse` do Google Forms configurado em `app.py`.

## Executar

```powershell
cd C:\Users\massa\Documents\ChatGPT\AguaViva2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Abra:

```text
http://127.0.0.1:5000
```

## Funcionalidades

- cadastro do ponto de monitoramento;
- coordenadas manuais ou captura via GPS do navegador;
- data da coleta com atalhos de dia anterior, proximo dia e hoje;
- avaliacao sensorial e fisico-quimica por notas 1, 2 e 3;
- calculo automatico de score, IQA de campo e classificacao;
- rascunho automatico no navegador;
- confirmacao com URL final gerada para o Google Forms;
- modulo Mapa lendo registros do Google Sheets publicado como CSV;
- modulo Formulas com expressoes locais;
- modulo Admin com resumo, classificacoes e fila local;
- modulo Perfil com status de sincronizacao;
- cache SQLite local para leitura offline e envios pendentes.

## Observacao

O campo `endereco` nao existe na URL original do Google Forms. Por isso, quando informado, ele e anexado ao campo de observacoes antes do envio.

O banco SQLite local (`aguaviva_local.sqlite3`) e usado somente como cache/fila offline. Quando houver conexao, os novos registros continuam sendo enviados ao Google Forms e as consultas usam o CSV publicado do Google Sheets.
