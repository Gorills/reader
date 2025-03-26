# Установка докера 
# sudo apt update
# sudo apt install -y docker.io


# sudo systemctl start docker
# sudo systemctl enable docker
# sudo systemctl status docker


# sudo mkdir -p /usr/local/lib/docker/cli-plugins
# sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
# sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# git clone https://github.com/Gorills/reader.git
# cd reader
# docker compose build


# Запуск контейнеров
# docker compose up --scale reader=5 -d