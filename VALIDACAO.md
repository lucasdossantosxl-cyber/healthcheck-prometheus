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
| Prometheus target UP / alerta firing | **Não validado em execução**, por falta de espaço para os containers |
| Grafana com dashboard e dados | **Não validado em execução**, pela mesma limitação; arquivos de provisioning e dashboard incluídos |
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

Execute o procedimento do README: subir os quatro serviços, verificar o target UP,
abrir o dashboard, parar o demo por tempo suficiente para `TargetDown` ficar firing,
reiniciar o demo e verificar a resolução do alerta. Finalize com
`docker compose down` e confira `docker compose ps -a`.

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
