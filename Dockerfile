# Usa a imagem oficial do Python
FROM python:3.11

# Cria e usa o diretório de trabalho
WORKDIR /app

# Copia todos os arquivos do repositório
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pelo Flask
EXPOSE 8080

# Comando para iniciar o bot
CMD ["python", "bot.py"]
