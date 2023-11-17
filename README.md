setup. 

install python (if not alrady included)

`sudo apt-get install python3.9`` <--- no higher than 3.9

install docker

Follow the directions here
- `curl -fsSL https://get.docker.com -o get-docker.sh`
- `chmod +x get-docker.sh`
- `sudo ./get-docker.sh`

clone this repo
use branch `docker`

Put a .env file in the project root with the following variables

```
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=adminpassword
ME_CONFIG_BASICAUTH_USERNAME=expressadmin
ME_CONFIG_BASICAUTH_PASSWORD=expresspassword
SCRAPYDWEB_USERNAME=myusername
SCRAPYDWEB_PASSWORD=mypassword
```

Change above variables as appropriate 

mkdir -p ~/scrapy_flyertalk_data/scrapyd/logs

give docker permissions for the above dir

`sudo usermod -aG docker $USER`

install pop
`sudo apt install python3-pip`

install scrapyd-client
`pip install scrapyd-client`

install setuptools 
`pip install setuptools`

`cd ~/scrapy_flyertalk`

start the containers
`sudo docker compose up -d`

3 endpoints should be exposed at ports: 

Make these acessible/forward them somehow. 

- `5001`: scrapyd web
- `8081`: mongo express (web ui for mongo)
- `6800`: minimal web ui for scrapyd

deploying scrapy. 

run the following command to egg the project and upload it to the scrapyd


`scrapyd-deploy default -p flyertalk --include-dependencies`
