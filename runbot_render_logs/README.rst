.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===========================
Render Logs
===========================

This module add a live logs of runbot builds, to see it have to do the following:

Go to the build menu and select "Live Logs"

 .. image:: https://raw.githubusercontent.com/Vauxoo/runbot-addons/9.0/runbot_sender_logs/static/img/README_01.png

There will be displayed a blank screen where files will appear having modification, but you should be selecting the files you want to display once they are added to the list on the left:

 .. image:: https://raw.githubusercontent.com/Vauxoo/runbot-addons/9.0/runbot_sender_logs/static/img/README_02.png


Requirements:
-------------

- `runbot_travis2docker` module.

Configuration requirements:
---------------------------

Detecting the container name

```
docker exec -it CONTAINER_ID python -c "import socket;print socket.getfqdn()"
```

Detecting the container IP

```
docker inspect CONTAINER_ID
```

On Host
Install dnsmasq

```
sudo apt-get install dnsmasq
echo "address=/.CONTAINER_ID/IP_CONTAINER >> /etc/dnsmasq.conf
```

Add the container IP and name into /etc/hosts

/etc/hosts

```
IP_CONTAINER NAME_SOCKET_GETFDQDN
IP_CONTAINER CONTAINER_ID
```


Modify or Add the nginx file /etc/nginx/sites-enabled/site-runbot.conf in container

```
   upstream runbot2 {

      server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=200m;

   }

   server {

      listen 80;

      server_name ~^(.*)\.CONTAINER_ID$ CONTAINER_ID;

      location / {

         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

         proxy_set_header Host $host;

         send_timeout 200m;

         proxy_read_timeout 200m;

         proxy_connect_timeout 200m;

         proxy_pass    http://runbot2;

      }

   }

```

Contributors
------------

* Nhomar Hernandez <nhomar@vauxoo.com>
* Tulio Ruiz <tulio@vauxoo.com>
* Moises Lopez <moylop260@vauxoo.com>
* Luis Escobar <lescobar@vauxoo.com>

Maintainer
----------

.. image:: https://www.vauxoo.com/logo.png
   :alt: Vauxoo
   :target: https://vauxoo.com

This module is maintained by Vauxoo.

a latinamerican company that provides training, coaching,
development and implementation of enterprise management
sytems and bases its entire operation strategy in the use
of Open Source Software and its main product is odoo.

To contribute to this module, please visit http://vauxoo.com.
