# Keboola Odoo ERP Implementation

Odoo 18.0 Community Edition on Google Cloud Platform

## Environment

| Component | Value |
|-----------|-------|
| Platform | GCP VM (odoo-1-vm) |
| Zone | europe-north1-c |
| Project | odoo-crm-461310 |
| Production URL | https://erp.internal.keboola.com |
| Staging URL | http://34.88.2.228:8069 |
| Database | PostgreSQL (keboola-community) |
| Internal IP | 10.166.0.4 |
| External IP | 35.228.61.117 |

---

## Critical Safety Rules

### NEVER Delete Without Explicit Request

| Table | Why Protected |
|-------|---------------|
| **res_users** | Breaks authentication and OAuth |
| **res_company** | Breaks accounting and multi-company architecture |

### Before Any Database Operation

1. **Create backup first**
2. **Preview with SELECT** before DELETE
3. **Use transactions** (BEGIN/COMMIT/ROLLBACK)
4. **Ask for confirmation** if request is ambiguous

### Safe vs Unsafe Operations

| Safe to Delete | Unsafe to Delete |
|----------------|------------------|
| hr_employee | res_users |
| hr_leave | res_company |
| hr_contract | res_partner (linked to users) |
| hr_leave_allocation | res_partner (linked to companies) |

### Example Safe Contact Cleanup

```sql
-- Only deletes contacts NOT linked to users or companies
DELETE FROM res_partner
WHERE id NOT IN (
    SELECT partner_id FROM res_users WHERE partner_id IS NOT NULL
    UNION
    SELECT partner_id FROM res_company WHERE partner_id IS NOT NULL
);
```

---

## Quick Access

### SSH to Production

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310
```

### SSH to Staging

```bash
gcloud compute ssh odoo-staging-vm --zone=europe-north1-c --project=odoo-crm-461310
```

### Database Access (On VM)

```bash
sudo -u postgres psql -d keboola-community
```

### API Access (XML-RPC)

```
URL:      https://erp.internal.keboola.com
Database: keboola-community
Username: svc-odoo-bamboo-integration@keboola.com
Password: gzd2YQB9pbe_gxc8kam
```

### GCP Secrets

Credentials are securely stored in Google Secret Manager. Retrieve them using:

```bash
# List available secrets
gcloud secrets list

# Retrieve a specific secret (e.g., Staging Admin Password)
gcloud secrets versions access latest --secret="odoo-staging-admin-password"
```

**Available Secrets:**
*   `odoo-production-admin-password`
*   `odoo-production-db-password`
*   `odoo-production-postgres-master-password`
*   `odoo-staging-admin-password`
*   `odoo-staging-db-password`
*   `odoo-staging-postgres-master-password`

### Restart Odoo Service

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo systemctl restart odoo"
```

### View Odoo Logs

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo tail -f /var/log/odoo/odoo-server.log"
```

---

## Quick Employee Cleanup (Bamboo Sync Testing)

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 --command="sudo -u postgres psql -d keboola-community << 'EOF'
BEGIN;
DELETE FROM hr_leave_allocation;
DELETE FROM hr_leave;
DELETE FROM hr_contract;
DELETE FROM resource_calendar_leaves;
DELETE FROM dms_file;
DELETE FROM ir_attachment WHERE res_model = 'hr.employee';
DELETE FROM hr_employee;
COMMIT;
EOF"
```

**Deletes:** Employees, contracts, time off, allocations, DMS files, employee attachments
**Preserves:** Users, companies, partners

---

## Staging Environment

Daily automatic sync at **2:00 AM UTC** via systemd timer.

### Manual Sync

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
    --command="sudo /opt/scripts/sync-to-staging.sh"
```

See [Staging Operations](docs/operations/STAGING_SYNC.md) for detailed commands.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md) | Custom modules and deployment |
| [BAMBOO_SYNC_CLEANUP.md](docs/operations/BAMBOO_SYNC_CLEANUP.md) | Employee data cleanup guide |
| [CONTACT_CLEANUP.md](docs/operations/CONTACT_CLEANUP.md) | Contact/partner cleanup guide |
| [USER_DELETION.md](docs/operations/USER_DELETION.md) | User deletion guide |
| [STAGING_SYNC.md](docs/operations/STAGING_SYNC.md) | Staging sync operations |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sync-to-staging.sh` | Export production data to GCS |
| `scripts/restore-from-gcs.sh` | Restore staging from GCS |
| `scripts/deploy-sync-scripts.sh` | Deploy scripts to VMs |
| `scripts/odoo-sync.service` | Systemd service definition |
| `scripts/odoo-sync.timer` | Systemd timer (2:00 AM daily) |

---

## Custom Modules

### hr_contract_employee_visibility (v18.0.1.6.0)

**Fixes:**
- Contracts button visible for contractors on employee form
- All Contracts button visible for contractors on contract form
- Contracts count shows correct number (not 0)

**Location:** `/var/lib/odoo/.local/share/Odoo/addons/18.0/hr_contract_employee_visibility/`

### web_responsive (OCA)

**Features:**
- Enterprise-like app grid home screen (instead of Discuss redirect)
- Full-screen app menu with quick search
- Responsive design for mobile/tablet

**Location:** `/opt/odoo/custom-addons/oca_web/web_responsive/`

**Note:** Requires `is_redirect_home = true` in user preferences. See `scripts/cloud-shell/update_home_screen_all_users.sh`.

See [CUSTOMIZATIONS.md](docs/CUSTOMIZATIONS.md) for details.

---

## SQL Files

| File | Purpose |
|------|---------|
| `sql/delete_all_employees.sql` | Delete all employees and dependencies |

---

## Recovery Options

If users/companies are accidentally deleted:

1. Check VM snapshots in GCP console
2. Check `/tmp/` for `.dump` or `.sql.gz` files
3. Use pg_restore to restore from backup
4. Contact infrastructure team

---

## Folder Structure

```
erp-odoo-implementation/
├── README.md                    # This file (main documentation)
├── agent.md -> README.md        # AI symlink
├── claude.md -> README.md       # AI symlink
├── docs/
│   ├── CUSTOMIZATIONS.md        # Custom modules documentation
│   └── operations/
│       ├── BAMBOO_SYNC_CLEANUP.md
│       ├── CONTACT_CLEANUP.md
│       ├── USER_DELETION.md
│       └── STAGING_SYNC.md
├── scripts/
│   ├── sync-to-staging.sh
│   ├── restore-from-gcs.sh
│   ├── deploy-sync-scripts.sh
│   ├── odoo-sync.service
│   └── odoo-sync.timer
└── sql/
    └── delete_all_employees.sql
```

---

## Support

- **Odoo Documentation:** https://www.odoo.com/documentation/18.0/
- **GCP Documentation:** https://cloud.google.com/docs

---

**Last Updated:** December 27, 2025
**Maintained By:** Platform Team
