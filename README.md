
# README

## Update the following files

update weather_underground_api.py

update vfd.service for path to vfd.py

update vfd.py to assign serial ports

## Enable the service

```
$ sudo cp vfd.service /lib/systemd/system/

$ sudo systemctl daemon-reload

$ sudo systemctl enable vfd.service
$ sudo systemctl start vfd.service

$ sudo systemctl status vfd.service
```
