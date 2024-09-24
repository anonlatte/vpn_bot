FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/anonlatte/vpn_bot .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]