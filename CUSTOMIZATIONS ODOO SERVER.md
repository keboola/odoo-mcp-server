# Odoo ERP Customizations

This document covers all custom modules and modifications deployed on the Keboola Odoo ERP system.

## Environment

| Component | Value |
|-----------|-------|
| Project ID | odoo-crm-461310 |
| VM Instance | odoo-1-vm |
| Zone | europe-north1-c |
| Odoo Version | 18.0 Community |
| Internal IP | 10.166.0.4 |
| External IP | 35.228.61.117 |

---

## Custom Modules

### 1. hr_contract_employee_visibility (v18.0.1.6.0)

**Status:** Installed and Active
**Purpose:** Fixes contractor visibility issues for contracts buttons

#### What It Fixes

| Issue | Before | After |
|-------|--------|-------|
| Employee Form - Contracts button | Hidden for contractors | Visible |
| Contract Form - All Contracts button | Hidden for contractors | Visible |
| Contracts count | Shows 0 for contractors | Shows correct count |

#### Employee Type Visibility Matrix

| Employee Type | Contracts Button Visible |
|---------------|--------------------------|
| Employee | Yes |
| Student | Yes |
| Trainee | Yes |
| Contractor | **Yes (Custom)** |
| Freelancer | No |
| Worker | No |

#### Module Location

```
/var/lib/odoo/.local/share/Odoo/addons/18.0/hr_contract_employee_visibility/
├── __init__.py                      # Module entry point
├── __manifest__.py                  # Module metadata (v18.0.1.6.0)
├── models/
│   ├── __init__.py                  # Model imports
│   ├── hr_contract.py               # Adds employee_type_related field
│   └── hr_employee.py               # Fixes contracts_count computation
└── views/
    └── hr_employee_views.xml        # Button visibility modifications
```

#### Technical Implementation

**1. Employee Form Button (hr_employee_views.xml)**
```xml
<xpath expr="//button[@name='action_open_contract']" position="attributes">
    <attribute name="invisible">employee_type not in ['employee', 'student', 'trainee', 'contractor']</attribute>
</xpath>
```

**2. Contract Form Button (hr_employee_views.xml)**
```xml
<xpath expr="//button[@name='action_open_contract_list']" position="attributes">
    <attribute name="invisible">contracts_count == 0 and employee_type_related != 'contractor'</attribute>
</xpath>
```

**3. Contracts Count Fix (hr_employee.py)**
```python
@api.depends('contract_ids')
def _compute_contracts_count(self):
    for employee in self:
        employee.contracts_count = len(employee.contract_ids)
```

---

### 2. hr_employee_custom_fields (v18.0.1.2.0)

**Status:** Installed and Active
**Purpose:** Adds custom fields for BambooHR sync

#### Custom Fields Added

| Field | Technical Name | Location |
|-------|---------------|----------|
| Division | x_division | Employee form and list |
| Preferred Name | x_preferred_name | Employee form only |

#### Module Location

```
/var/lib/odoo/.local/share/Odoo/addons/18.0/hr_employee_custom_fields/
├── __init__.py
├── __manifest__.py
└── views/
    └── hr_employee_views.xml
```

---

## OCA Modules

### 3. web_responsive (OCA)

**Status:** Installed and Active
**Source:** [Odoo Community Association (OCA)](https://odoo-community.org/shop/web-responsive-2681)
**Purpose:** Provides Enterprise-like app grid home screen for Odoo Community

#### What It Does

| Feature | Description |
|---------|-------------|
| App Grid Home Screen | Shows application icons on login instead of redirecting to Discuss |
| Full-screen App Menu | Navigation menu becomes a full-screen app launcher |
| Quick Menu Search | Auto-focused search at top for faster navigation |
| Responsive Design | Better mobile/tablet experience |

#### Module Location

```
/opt/odoo/custom-addons/oca_web/web_responsive/
```

**Important:** The OCA modules are in a subdirectory. The Odoo config must include:
```
addons_path = .../custom-addons/oca_web
```

#### User Settings

The home screen behavior is controlled by user preferences in `res_users` table:

| Setting | Value | Effect |
|---------|-------|--------|
| `is_redirect_home` | `true` | Shows app grid on login |
| `action_id` | `NULL` | Prevents redirect to specific app (e.g., Discuss) |

#### Enabling for All Users

Run the script to enable for all active users:

```bash
# From Cloud Shell or local machine
./scripts/cloud-shell/update_home_screen_all_users.sh
```

Or manually via SQL:

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo -u postgres psql -d keboola-community -c \"UPDATE res_users SET is_redirect_home = true, action_id = NULL WHERE active = true;\""
```

#### Staging Configuration

**Critical:** After syncing to staging, verify the Odoo config includes the correct addons path:

```bash
# Check staging config
gcloud compute ssh odoo-staging-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo cat /etc/odoo/odoo.conf | grep addons_path"

# Should include: /opt/odoo/custom-addons/oca_web
# If missing, update and restart:
gcloud compute ssh odoo-staging-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo sed -i 's|/opt/odoo/custom-addons|/opt/odoo/custom-addons/oca_web|' /etc/odoo/odoo.conf && sudo systemctl restart odoo"
```

#### Troubleshooting

**Home screen not showing app grid:**

1. Verify module is installed:
   ```sql
   SELECT name, state FROM ir_module_module WHERE name = 'web_responsive';
   ```

2. Verify user settings:
   ```sql
   SELECT login, is_redirect_home, action_id FROM res_users WHERE active = true;
   ```

3. Check addons_path includes `/oca_web` subdirectory

4. Restart Odoo and clear browser cache (Ctrl+Shift+R)

---

### 4. dms (OCA)

**Status:** Installed and Configured on Staging
**Source:** [OCA/dms](https://github.com/OCA/dms)
**Purpose:** HR Document Management System with strict access controls and Odoo 18 compatibility.

#### Architecture: `Employee > Category`
The system is optimized for Employee Self-Service. Each employee has a personal root folder containing sub-folders (Contracts, Identity, etc.).

#### Key Security Features
- **Privacy:** Employees cannot see other employees' folders.
- **Restricted Folders:** "Background Checks" and "Offboarding Documents" are hidden from employees even within their own folder.
- **Identity Upload:** Employees can upload new Identity Documents but cannot delete existing ones.

---

### 5. hr_employee_dms_smart_button (Custom)

**Status:** Installed and Active
**Purpose:** Bridges the gap between HR Profiles and DMS.
**Features:**
- **Smart Button:** "Documents" button in the top right of Employee card.
- **Native Tab:** Replaces the broken OCA tab with a reliable Odoo list of authorized documents.
- **Python Safety Filter:** A hardcoded layer in the model to ensure restricted documents never leak to the UI.

---

## Production Replication Guide

Follow these steps exactly to replicate the DMS setup on the Production environment.

### Phase 1: Module Installation
```bash
# SSH to Production VM
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310

# 1. Clone OCA DMS Repository
sudo rm -rf /tmp/dms_repo
sudo git clone --branch 18.0 --depth 1 https://github.com/OCA/dms /tmp/dms_repo

# 2. Deploy required modules to custom-addons
sudo mkdir -p /opt/odoo/custom-addons/oca_dms
sudo cp -r /tmp/dms_repo/dms /opt/odoo/custom-addons/oca_dms/
sudo cp -r /tmp/dms_repo/dms_field /opt/odoo/custom-addons/oca_dms/
sudo cp -r /tmp/dms_repo/hr_dms_field /opt/odoo/custom-addons/oca_dms/
sudo rm -rf /tmp/dms_repo

# 3. Deploy Custom Smart Button Module (from this repo)
# Use 'gcloud compute scp' to upload modules/hr_employee_dms_smart_button to /opt/odoo/custom-addons/oca_dms/

# 4. Permissions & Restart
sudo chown -R odoo:odoo /opt/odoo/custom-addons/oca_dms
sudo systemctl restart odoo
```

### Phase 2: Initialization Script
Run `scripts/vm/setup_dms.py` on the Production VM (update the URL and fetch the production admin password from GCP Secrets first). This script will:
- Create the "HR Documents" Root.
- Create the `_Structure_Template`.
- Configure the "DMS HR Officer" and "DMS Employee Read" access groups.

### Phase 3: Critical Odoo 18 Fixes (SQL)
The OCA DMS module has known compatibility issues with Odoo 18's strict type checking and record rule logic. **Run these SQL commands on the production database:**

```sql
-- 1. Fix Directory Read Rule (Relational instead of Computed)
UPDATE ir_rule 
SET domain_force = '[(''complete_group_ids.users'', ''in'', [user.id])]' 
WHERE name = 'Apply computed read permissions.' AND model_id = (SELECT id FROM ir_model WHERE model = 'dms.directory');

-- 2. Fix File Read Rule
UPDATE ir_rule 
SET domain_force = '[(''directory_id.complete_group_ids.users'', ''in'', [user.id])]' 
WHERE name = 'Apply computed read permissions.' AND model_id = (SELECT id FROM ir_model WHERE model = 'dms.file');

-- 3. FIX: Make Computed Rules Non-Global (Required for Manager Overrides)
-- In Odoo 18, Global rules are joined with AND. Computed rules must be Non-Global 
-- to allow the "DMS Manager Full Access" rule to override them.
UPDATE ir_rule SET global = false 
WHERE name IN ('Apply computed read permissions.', 'Apply computed create permissions.', 
               'Apply computed unlink permissions.', 'Apply computed write permissions.') 
AND model_id IN (SELECT id FROM ir_model WHERE model IN ('dms.directory', 'dms.file'));

-- 4. Link Computed Rules to DMS User Group (ID 86)
-- This ensures they still apply to regular users while allowing Manager (ID 87) bypass.
INSERT INTO rule_group_rel (rule_group_id, group_id)
SELECT id, 86 FROM ir_rule 
WHERE name IN ('Apply computed read permissions.', 'Apply computed create permissions.', 
               'Apply computed unlink permissions.', 'Apply computed write permissions.') 
AND model_id IN (SELECT id FROM ir_model WHERE model IN ('dms.directory', 'dms.file'))
ON CONFLICT DO NOTHING;

-- 5. Create DMS Manager Bypass Rules
INSERT INTO ir_rule (name, model_id, active, domain_force, perm_read, perm_write, perm_create, perm_unlink, global) 
VALUES ('DMS Manager Full Access (Dir)', (SELECT id FROM ir_model WHERE model = 'dms.directory'), true, '[(1, ''='', 1)]', true, true, true, true, false),
       ('DMS Manager Full Access (File)', (SELECT id FROM ir_model WHERE model = 'dms.file'), true, '[(1, ''='', 1)]', true, true, true, true, false)
ON CONFLICT DO NOTHING;

-- 6. Link Bypass Rules to DMS Manager Group (ID 87)
INSERT INTO rule_group_rel (rule_group_id, group_id)
SELECT id, 87 FROM ir_rule WHERE name LIKE 'DMS Manager Full Access%'
ON CONFLICT DO NOTHING;

-- 7. Disable the 'Locked files' bypass rule
UPDATE ir_rule SET active = false WHERE name = 'Locked files are only modified by locker user.';
```

### Phase 4: Permission Cache Recompute
Run the following in the Odoo shell to ensure all existing files (if any) pick up the new security logic:
```python
# sudo /opt/odoo/venv/bin/python3 /opt/odoo/odoo/odoo-bin shell -c /etc/odoo/odoo.conf -d keboola-community
dirs = env['dms.directory'].search([])
for d in dirs:
    old = d.inherit_group_ids
    d.write({'inherit_group_ids': not old})
    d.write({'inherit_group_ids': old})
env.cr.commit()
```

---

## Deployment

### Fresh Module Installation

```bash
# SSH to Odoo VM
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310

# Create module structure
sudo mkdir -p /var/lib/odoo/.local/share/Odoo/addons/18.0/hr_contract_employee_visibility/models/views
sudo chown -R odoo:odoo /var/lib/odoo/.local/share/Odoo/addons/18.0/hr_contract_employee_visibility/
```

### Module Installation Script

```python
#!/usr/bin/env python3
import xmlrpc.client
import ssl

ODOO_URL = "https://erp.internal.keboola.com"
ODOO_DB = "keboola-community"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "YOUR_PASSWORD"

ssl_context = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', context=ssl_context)
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', context=ssl_context)

# Update module list
models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'ir.module.module', 'update_list', [[]])

# Find and install module
module_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
    'ir.module.module', 'search',
    [[['name', '=', 'hr_contract_employee_visibility']]])

if module_ids:
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        'ir.module.module', 'button_immediate_install', [module_ids])
    print("Module installed successfully!")
```

### Restart Odoo After Changes

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo systemctl restart odoo"
```

---

## Troubleshooting

### Button Not Visible After Installation

1. **Hard refresh browser:** Ctrl+Shift+R
2. **Clear browser cache completely**
3. **Restart Odoo service**
4. **Check module status:** Verify module is installed in Apps menu
5. **Verify user permissions:** User needs HR Contract Manager group

### Module Not Found

```bash
# Check files exist
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo ls -la /var/lib/odoo/.local/share/Odoo/addons/18.0/hr_contract_employee_visibility/"
```

### Count Shows 0

- Restart Odoo
- Check module version is 18.0.1.6.0
- Verify hr_employee.py exists

---

## Rollback

### Uninstall Module

```python
#!/usr/bin/env python3
import xmlrpc.client
import ssl

ODOO_URL = "https://erp.internal.keboola.com"
ODOO_DB = "keboola-community"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "YOUR_PASSWORD"

ssl_context = ssl._create_unverified_context()
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', context=ssl_context)
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', context=ssl_context)

module_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
    'ir.module.module', 'search',
    [[['name', '=', 'hr_contract_employee_visibility']]])

if module_ids:
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        'ir.module.module', 'button_immediate_uninstall', [module_ids])
    print("Module uninstalled")
```

### Module Backup

```bash
gcloud compute ssh odoo-1-vm --zone=europe-north1-c --project=odoo-crm-461310 \
  --command="sudo tar -czf /tmp/hr_contract_employee_visibility.tar.gz -C /var/lib/odoo/.local/share/Odoo/addons/18.0/ hr_contract_employee_visibility"

gcloud compute scp odoo-1-vm:/tmp/hr_contract_employee_visibility.tar.gz . \
  --zone=europe-north1-c --project=odoo-crm-461310
```

---

## Testing Checklist

After deployment, verify:

- [ ] Open contractor employee form
- [ ] "Contracts" button is visible in top right
- [ ] Button shows correct count (not 0)
- [ ] Button opens contracts list when clicked
- [ ] Open a contract for contractor
- [ ] "All Contracts" button is visible
- [ ] Button opens all contracts when clicked
- [ ] Security: Only HR managers see buttons
- [ ] Hard refresh browser (Ctrl+Shift+R)

**Test URLs:**
- Employee: https://erp.internal.keboola.com/odoo/employees/{id}
- Contract: https://erp.internal.keboola.com/odoo/employees/{id}/employee-contracts/{contract_id}

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 18.0.1.0.0 | 2025-11-10 | Initial - Employee form button |
| 18.0.1.5.0 | 2025-11-10 | Contract form button visible |
| 18.0.1.6.0 | 2025-11-11 | Contracts count fixed |
| 18.0.1.2.0 | 2025-10-26 | Custom fields module |
| OCA | 2025-12-24 | web_responsive module installed for app grid home screen |

---

**Last Updated:** December 27, 2025
**Status:** Production Ready
