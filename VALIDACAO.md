# Relatório de validação — 12/11/2026

Executado em um ambiente cloud Linux com Python 3.12.14 e, posteriormente,
em runners Ubuntu 24.04 do GitHub Actions com Python 3.12 e 3.13.
Não foi executado no Mac do usuário.

| Etapa | Resultado |
| --- | --- |
| Testes pytest | **50 passaram**, com mocks e sem chamadas à internet; também executados em Python 3.12 e 3.13 na CI |
| Dependências | `pip check`: sem dependências quebradas |
| Configuração | Arquivos YAML e JSON parseados com sucesso |
| Portas antes da execução | 3000, 8000, 8080 e 9090 livres |
| Build do checker | **Passou**, após fornecer o certificado público do proxy cloud via secret temporário de build |
| Compose com quatro serviços saudáveis | **Passou na CI** com build e healthchecks; a tentativa inicial neste ambiente cloud foi bloqueada pelo disco de 7,9 GB |
| Quatro métricas em `/metrics` | **Passou** executando checker e demo como processos Python locais |
| Falha e recuperação do checker | **Passou**: parar demo mudou `healthcheck_up` para 0; iniciar demo restaurou 1 |
| SIGTERM do checker | **Passou**: servidor encerrado e processo com código de saída 0 |
| Regras de alerta | **Passou**: `promtool` 3.3.0 validou duas regras e três cenários de espera, disparo e recuperação |
| Prometheus target UP / alerta firing | **Passou na CI**: `TargetDown` e `CheckerDown` dispararam nas respectivas falhas e se resolveram após recuperação; `TargetDown` também validado localmente |
| Grafana com dashboard e dados | **Passou**: dashboard e datasource conectados na CI; interface validada localmente com três capturas reais incluídas em `docs/` |
| Encerramento | `docker compose down` executado sem `-v`, com confirmação de ausência dos containers do projeto, na CI e na tentativa local; processos locais encerrados |

## Erros reais encontrados

1. Na primeira tentativa de build, o pip encontrou
   `SSLCertVerificationError: certificate verify failed: self-signed certificate in certificate chain`.
   O proxy cloud exige uma CA própria. A segunda tentativa usou um secret opcional
   do BuildKit (`build_ca`), sem desativar HTTPS e sem gravar a CA na imagem/repositório.
   A instalação e o build terminaram com sucesso.
2. Na criação dos containers, o Docker retornou
   `Error response from daemon: mkdir .../ossl-modules: no space left on device`.
   Os recursos criados por este Compose foram encerrados. Não foram executados
   comandos globais de limpeza nem removidos os volumes.

## Limite do ambiente cloud local

A execução conjunta dos quatro containers foi validada na CI, incluindo rede,
mounts e healthchecks. O limite de disco continua impedindo repetir esse teste
neste ambiente cloud local. A coleta, o alerta e o dashboard também foram
validados como processos locais, conforme descrito abaixo. Para executar o
laboratório no computador pessoal, siga o procedimento do README.

## Capturas reais do dashboard

Para contornar o limite de disco do Docker neste ambiente, foram executados
os binários oficiais do Prometheus 3.3.0 e do Grafana 11.6.0 como processos locais,
junto com o checker e o demo-app. Os downloads tiveram seus SHA256 conferidos
com os checksums oficiais. Não foram usados dados sintéticos nem imagens geradas.

As configurações temporárias ficaram dentro de `work/`, ignorado pelo Git.
Apenas os endereços entre serviços e os caminhos de provisioning foram adaptados
para o host local. Foram preservados o dashboard, as métricas, os intervalos de
checagem e scrape de 15 segundos, o timeout de 5 segundos e a regra `TargetDown`
com `for: 1m` do projeto. O armazenamento temporário do Prometheus foi limitado
para caber no disco disponível.

O teste verificou a sequência `healthcheck_up = 1 → 0 → 1`, o alerta em estado
`firing` durante a falha e sua resolução após o retorno do demo-app. Os quatro
painéis foram renderizados em Chromium com dados, sem erros JavaScript. As
capturas usam as janelas históricas reais de cada etapa:

- `docs/dashboard-normal.png`: alvo disponível antes da falha.
- `docs/dashboard-falha.png`: alvo indisponível e falhas acumuladas.
- `docs/dashboard-recuperacao.png`: alvo disponível novamente, mantendo o histórico.

O período de coleta foi curto: o percentual de disponibilidade representa as
checagens desse laboratório, não um histórico completo de 24 horas. As cores do
painel de disponibilidade foram explicitadas: abaixo de 95% em vermelho, de 95%
até menos de 99% em laranja e a partir de 99% em verde. São faixas visuais de
demonstração, não um SLO configurado. Todos os processos locais foram encerrados
ao final.

O projeto foi construído usando Python 3.12 para manter a mesma versão no host
de testes e na imagem. O Python 3.15 mencionado no pedido não foi usado nem validado.

## Melhorias posteriores

- Configuração: rejeita chaves YAML duplicadas, opções desconhecidas e URLs
  HTTP malformadas antes de iniciar. URLs IPv6 e hostnames Unicode têm testes
  de compatibilidade. Falhas de UTF-8 e números grandes geram erros de validação.
- Logs: as bibliotecas HTTP deixam de registrar URLs completas em INFO/DEBUG.
  Testes cobrem sucesso, erro HTTP e falha de conexão, preservando os logs do
  alvo e resultado sem expor caminho ou query da URL.
- Monitoramento: `CheckerDown` detecta falhas de coleta do próprio checker,
  enquanto `TargetDown` continua acompanhando a URL. Os testes de regras verificam
  que ambos aguardam um minuto, disparam e se resolvem na recuperação.
- Automação: a CI usa actions fixadas por SHA, Node.js 24 e Ubuntu 24.04.
  O script de smoke test verifica portas antes de subir o Compose e usa timeouts
  explícitos; o teste negativo confirmou que serviços ausentes provocam falha,
  em vez de um resultado positivo indevido.

### Resultado da CI completa

[Execução aprovada no GitHub Actions](https://github.com/lucasdossantosxl-cyber/healthcheck-prometheus/actions/runs/43251506320),
referente ao commit `df81710bfad7ec19c90deb1daeb9e7d418db60ea`:

- Python 3.12: 50 testes aprovados e dependências verificadas.
- Python 3.13: 50 testes aprovados e dependências verificadas.
- Prometheus: configuração e testes de regras aprovados com `promtool` 3.3.0.
- Compose: quatro serviços saudáveis após build.
- Integração: quatro métricas, scrape UP, disponibilidade com dados e dashboard
  provisionado com conexão ao datasource confirmados.
- Falha e recuperação do demo-app: alerta `TargetDown` confirmado e resolvido.
- Falha e recuperação do checker: alerta `CheckerDown` confirmado e resolvido.
- Encerramento: Compose finalizado, sem containers do projeto restantes.

## Git e publicação

Conta autenticada conferida: `lucasdossantosxl-cyber`. A identidade Git foi
configurada apenas neste repositório, com o endereço noreply da conta pessoal.
A revisão dos arquivos versionados não encontrou credenciais ou referências
corporativas. O código foi organizado em commits locais separados.

A tentativa inicial de criar o repositório público pela integração falhou com:
`GraphQL: Resource not accessible by integration (createRepository)`.
Após o usuário criar o repositório vazio, o push da branch `main` foi realizado
com sucesso em https://github.com/lucasdossantosxl-cyber/healthcheck-prometheus.
O repositório é público. Nenhuma configuração global ou credencial foi alterada.
