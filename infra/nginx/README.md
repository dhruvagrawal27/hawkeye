# Host nginx configuration for HAWKEYE

This directory contains the nginx server block for `hawkeye.nineagents.in`.

## Installation (one-time)

```bash
# On the VPS
sudo cp hawkeye.nineagents.in.conf /etc/nginx/sites-available/hawkeye.nineagents.in
sudo ln -s /etc/nginx/sites-available/hawkeye.nineagents.in \
           /etc/nginx/sites-enabled/hawkeye.nineagents.in
sudo nginx -t
sudo systemctl reload nginx

# Issue TLS cert
sudo certbot --nginx -d hawkeye.nineagents.in \
  --email your@email.com --agree-tos --no-eff-email
```

## Coexistence with `/ngo`

The existing `/ngo` project uses the host's **default nginx server block**
(matched by the server's IP with no domain). HAWKEYE uses `server_name hawkeye.nineagents.in`.
They never collide because nginx routes by the `Host` HTTP header.

**Do not** add `default_server` to the HAWKEYE config.  
**Do not** modify any existing config files in `/etc/nginx/sites-enabled/`.

## Verify coexistence after deploy

```bash
curl -sI http://91.99.201.2/ngo
curl -sI http://91.99.201.2/ngo/dashboard
# Both should return HTTP 200 or 301
```
