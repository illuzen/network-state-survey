pip3 install -r ./api/requirements.txt
ape plugins install arbitrum polygon optimism fantom
ape plugins install .
ape compile ./contracts

sudo apt install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server