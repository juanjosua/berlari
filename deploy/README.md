# Deploying Berlari

Target: a small Ubuntu 24.04 box (tested on 1 vCPU / 1 GB RAM LXC container).

```bash
ssh root@your-server
git clone https://github.com/juanjosua/berlari.git /opt/berlari
bash /opt/berlari/deploy/setup.sh     # also used for updates
nano /opt/berlari/.env                # Strava keys + BASE_URL
systemctl restart berlari
```

The app listens on `127.0.0.1:8000`. Put something in front of it that provides HTTPS
(Strava OAuth and secure cookies need it), for example:

- **Caddy** if ports 80/443 reach the server: `reverse_proxy 127.0.0.1:8000` with your domain.
- **Cloudflare Tunnel** (`cloudflared`) if the server sits behind NAT with no open web ports.

Set `BASE_URL` to the public `https://` URL and put its host in the Strava app's
**Authorization Callback Domain**.

Logs: `journalctl -u berlari -f`
