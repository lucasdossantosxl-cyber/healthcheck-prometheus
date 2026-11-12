# Relatório de validação — 12/11/2026

Executado em um ambiente cloud Linux com Python 3.12.14, não no Mac do usuário.

| Etapa | Resultado |
| --- | --- |
| Testes pytest | **23 passaram**, com mocks e sem chamadas à internet |
| Dependências | `pip check`: sem dependências quebradas |
| Configuração | Arquivos YAML e JSON parseados com sucesso |
| Portas antes da execução | 3000, 8000, 8080 e 9090 livres |
| Build do checker | **Passou**, após fornecer o certificado público do proxy cloud via secret temporário de build |
| Compose com quatro serviços saudáveis | **Bloqueado**: `no space left on device` ao criar containers; filesystem do ambiente com 7,9 GB, 100% ocupado naquela etapa |
| Quatro métricas em `/metrics` | **Passou** executando checker e demo como processos Python locais |
| Falha e recuperação do checker | **Passou**: parar demo mudou `healthcheck_up` para 0; iniciar demo restaurou 1 |
| SIGTERM do checker | **Passou**: servidor encerrado e processo com código de saída 0 |
| Prometheus target UP / alerta firing | **Passou em execução local**, com Prometheus 3.3.0; `TargetDown` disparou e se resolveu após a recuperação |
| Grafana com dashboard e dados | **Passou em execução local**, com Grafana 11.6.0; três capturas reais incluídas em `docs/` |
| Encerramento | `docker compose down` executado sem `-v`; `docker compose ps -a` vazio; processos locais encerrados |

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

## Pendências para validar no computador local

A execução conjunta dos quatro containers pelo Compose ainda precisa ser validada
em uma máquina com espaço suficiente. Execute o procedimento do README para
confirmar também rede, mounts e healthchecks dos containers. A coleta, o alerta
e o dashboard já foram validados como processos locais, conforme descrito abaixo.

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
