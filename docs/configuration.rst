.. configuration:

=================
Configuration
=================

The only package specific configuration is given through the command line options.
You may however want to run a more 'robust' setup then simply starting the application in a screen session.
In order to do so, we will use systemd for starting our application and use apache2 as a reverse proxy.
We recommend not running this system on a broad subnet, because it is broadcasting over UDP, use a private subnet for the nodes if possible.

systemd
=======

Download our systemd example service file `dcron.service` from the repository and adapt where necessary.
Note that the most important thing is the user the service runs as, the user will need full application access for the cronlike jobs.

The usual spot for the file is `/etc/systemd/system/dcron.service`. After downloading and editing run `systemctl daemon-reload` for the service to show up.
Now run `systemctl start dcron` to check if everything is working. The webservice should be available under port 8080 (or whatever you configured).

apache2
=======

Our system doesn't do any authentication, so we will configure apache2 as a reverse proxy with authentication.

Install apache2: `apt install apache2`

Configure apach2 modules::

    a2enmod proxy
    a2enmod ssl
    a2ensite default-ssl.conf
    systemctl restart apache2

Edit /etc/apache2/sites-available/default-ssl.conf::

    <IfModule mod_ssl.c>
       <VirtualHost _default_:443>
               ServerAdmin [email protected]
               ServerName localhost
               DocumentRoot /var/www/html
               ErrorLog ${APACHE_LOG_DIR}/error.log
               CustomLog ${APACHE_LOG_DIR}/access.log combined
               SSLEngine on
               SSLCertificateFile /etc/ssl/certs/ssl-cert-snakeoil.pem
               SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key

               <FilesMatch "\.(cgi|shtml|phtml|php)$">
                               SSLOptions +StdEnvVars
               </FilesMatch>
               <Directory /usr/lib/cgi-bin>
                               SSLOptions +StdEnvVars
               </Directory>
               BrowserMatch "MSIE [2-6]" \
                               nokeepalive ssl-unclean-shutdown \
                               downgrade-1.0 force-response-1.0
               BrowserMatch "MSIE [17-9]" ssl-unclean-shutdown
               Alias /myservice/ /var/www/myservice/

               ProxyRequests On
               ProxyPreserveHost On

               <Proxy />
                   Order deny,allow
                   Allow from all
               </Proxy>


               <Location />
                 Order deny,allow
                 Allow from all

                 ProxyPass http://localhost:8080
                 ProxyPassReverse http://localhost:8080

                 AuthType Basic
                 AuthName "dcron"
                 AuthBasicProvider file
                 AuthUserFile /etc/apache2/.htpasswd

                 Require valid-user
               </Location>
         </VirtualHost>
    </IfModule>

Edit /etc/apache2/sites-available/000-default.conf::

    <VirtualHost *:80>
       #ServerName www.example.com

       ServerAdmin webmaster@localhost
       DocumentRoot /var/www/html

       ErrorLog ${APACHE_LOG_DIR}/error.log
       CustomLog ${APACHE_LOG_DIR}/access.log combined

       Redirect / https://external.machine.address
    </VirtualHost>

For every user you want to give access, run the following command:

`htpasswd -c /etc/apache2/.htpasswd <user>`

and enter a password.

You should now be good to go.