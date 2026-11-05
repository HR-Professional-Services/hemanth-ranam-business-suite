# Custom Domain & Cloudflare Wildcard Setup Guide
## Authoritative Domain: `hemanthranam.com`

This guide explains the exact steps to configure `hemanthranam.com` on Cloudflare so that unlimited client subdomains (`*.hemanthranam.com`) dynamically route to your SaaS platform with automatic SSL and zero incremental setup.

---

### Step 1: Add Domain to Cloudflare
1. Register `hemanthranam.com` at your preferred registrar (e.g. Cloudflare Registrar, Namecheap, Google Domains).
2. Change the domain's nameservers at your registrar to point to your Cloudflare nameservers (provided upon adding the domain in the Cloudflare dashboard).

---

### Step 2: Configure Wildcard DNS Records
In your Cloudflare dashboard under **DNS → Records**, add the following records:

```text
Type     Name    Content                       Proxy Status   TTL
CNAME    @       <YOUR_CLOUD_RUN_OR_EDGE_URL>  Proxied        Auto
CNAME    app     <YOUR_CLOUD_RUN_OR_EDGE_URL>  Proxied        Auto
CNAME    *       <YOUR_CLOUD_RUN_OR_EDGE_URL>  Proxied        Auto
```

- **`@` (Apex):** Points `hemanthranam.com` to your main company website or agency portfolio.
- **`app`:** Points `app.hemanthranam.com` to the central SaaS Control Plane.
- **`*` (Wildcard):** Automatically catches any client subdomain (`client1.hemanthranam.com`, `acme.hemanthranam.com`, `vanguard.hemanthranam.com`) and routes it to the same serverless origin.

---

### Step 3: Enable Universal SSL
Under **SSL/TLS → Edge Certificates**:
1. Set encryption mode to **Full (Strict)**.
2. Ensure **Universal SSL** is enabled (Cloudflare automatically issues a single wildcard certificate for `hemanthranam.com` and `*.hemanthranam.com`).
3. Enable **Always Use HTTPS** and **Automatic HTTPS Rewrites**.

---

### Step 4: Verification & Live Client Provisioning
Once DNS propagates:
1. Access the master control plane at `https://app.hemanthranam.com`.
2. Login with your `SUPER_ADMIN` credentials.
3. Click **+ Provision Client Tenant** and enter the client's information (e.g. slug: `acme`).
4. The client environment is immediately available at `https://acme.hemanthranam.com` with full SSL encryption and branded UI, requiring **zero further DNS changes**.
