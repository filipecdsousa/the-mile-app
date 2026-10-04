# The Mile — área privada

Primeira versão funcional, preparada para instalação. Ainda não publicada nem ligada a app.themile.pt. Não inclui palavras-passe, links ativos, contas de teste ou documentos de jogadores.

## Funcionalidades

- Dois administradores: Filipe Sousa (filipesousa@themile.pt) e Raquel Gomes (raquelgomes@themile.pt).
- Login com email e palavra-passe; sessões de 12 horas.
- Criar, ativar e desativar jogadores.
- Link privado, válido durante 24 horas e utilizável uma vez, para definir ou recuperar a palavra-passe.
- Três pastas fixas por jogador: Planos nutricionais, Menus e Outros documentos.
- Carregar, descarregar, substituir e apagar PDFs até 20 MB.
- Interface em português de Portugal e inglês. Os PDFs não são traduzidos.
- Permissões verificadas no servidor em todas as operações sobre documentos.

Os links são apresentados ao administrador para partilha manual. **Não há envio automático de emails nesta versão.** Os administradores não definem nem veem as palavras-passe dos jogadores. A recuperação do acesso de um administrador é feita pelo operador do alojamento através do comando `activate`.

## Experimentar localmente

Requer Python 3.12 ou superior. Não é preciso instalar dependências para o teste local.

```bash
python app.py init
python app.py activate --email filipesousa@themile.pt
python app.py activate --email raquelgomes@themile.pt
python app.py serve
```

Abrir cada link gerado em http://localhost:8000 e definir uma palavra-passe com pelo menos 12 caracteres. Depois entrar com o respetivo email. O servidor local é apenas para desenvolvimento.

## Instalação em alojamento

Esta versão requer um serviço Python ou Docker com **disco persistente**, HTTPS e um único servidor da aplicação. A base SQLite e os PDFs vivem no mesmo disco privado. Não instalar num serviço cujo disco é apagado em reinícios ou novas publicações. Não expor a pasta de dados como ficheiros públicos. Não é uma instalação WordPress nem um ficheiro para carregar diretamente num alojamento apenas de páginas estáticas.

Configuração:

```text
MILE_BASE_URL=https://app.themile.pt
MILE_DATA_DIR=/data
PORT=8000
```

Antes de ligar o domínio, usar como MILE_BASE_URL o endereço HTTPS temporário fornecido pelo alojamento. O valor tem de corresponder exatamente ao endereço usado pelos visitantes. Não usar HTTP em produção: o endereço HTTPS ativa cookies Secure e HSTS.

Sem Docker:

```bash
pip install -r requirements.txt
python app.py init
gunicorn wsgi:application --config gunicorn.conf.py
```

Documentação oficial do servidor WSGI: https://gunicorn.org/run/ e https://gunicorn.org/deploy/.

Com Docker:

```bash
docker build -t the-mile .
docker volume create mile-data
docker run -d --name the-mile -p 8000:8000 --mount source=mile-data,target=/data -e MILE_BASE_URL=https://app.themile.pt the-mile
docker exec the-mile python app.py activate --email filipesousa@themile.pt
docker exec the-mile python app.py activate --email raquelgomes@themile.pt
```

Colocar atrás de um proxy HTTPS. No proxy, limitar pedidos a 20 MB, definir timeout de upload e registar o IP real do visitante em REMOTE_ADDR para a limitação de tentativas. Não registar parâmetros de URLs: os links de ativação são secretos. Esta versão funciona numa única instância, adequada a um portal pequeno.

## Domínio Amen

Depois de publicar e testar, obter do serviço de alojamento o destino DNS e os registos de verificação exatos. No painel Amen, criar o registo de **app.themile.pt** com esses valores. O destino DNS ainda não existe e não deve ser inventado. Confirmar o certificado HTTPS e atualizar MILE_BASE_URL antes do uso real.

## Verificação e cópias de segurança

```bash
python -m unittest -v test_app.py
node --check static/app.js
```

Oito testes automatizados cobrem separação entre jogadores, acesso anónimo, limites de permissões, CSRF, origem dos pedidos, ativação e recuperação, desativação, validação de PDF, substituição, eliminação e limite de tentativas.

Estes testes verificam o servidor. A interface ainda requer uma passagem de verificação visual num browser após instalação. O pacote não foi instalado nem testado num alojamento remoto.

Fazer cópias de segurança cifradas de todo o diretório de dados, com a aplicação parada ou através de um snapshot consistente. Testar o restauro antes de carregar documentos reais. Os PDFs são ficheiros privados protegidos por permissões, mas não existe análise antivírus nesta versão. A retenção de dados e o serviço de alojamento devem ser definidos antes do uso com jogadores.
