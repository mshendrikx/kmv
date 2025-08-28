docker compose -f /home/ubuntu/apps/docker/docker-compose.yml down kmv
docker rmi mservatius/kmv:arm
docker build -t kmv:arm .
docker tag kmv:arm mservatius/kmv:arm
docker push mservatius/kmv:arm
docker rmi kmv:arm
docker rmi mservatius/kmv:arm
docker compose -f /home/ubuntu/apps/docker/docker-compose.yml up kmv -d