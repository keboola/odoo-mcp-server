# E2E QA Test Report - Odoo MCP Server (Comprehensive)

**Report Date:** 2026-01-08
**Test Environment:** Staging (https://odoo-mcp-server-55974118220.europe-west1.run.app/mcp)
**Tester:** Claude Code E2E QA Manager
**Test Method:** Claude.ai Chrome Integration with MCP tools
**OAuth Client ID:** 360932891826-6b82gjn5igtfihefq5cf68i45iquhtr9.apps.googleusercontent.com
**Test User:** jiri.manas@keboola.com (Jiri Manas - CTO)

---

## Executive Summary

This report documents comprehensive E2E testing of the Odoo MCP Server integration with Claude.ai, covering **62 test scenarios** across all employee self-service functions.

### Overall Status: **IN PROGRESS**

⚠️ **Performance Issue Detected:** MCP server responses are significantly slow (30-60+ seconds per tool call). This is impacting test execution speed.

| Category | Total | Pass | Fail | Pending | Requires Staging |
|----------|-------|------|------|---------|------------------|
| Setup & Auth | 4 | 4 | 0 | 0 | 0 |
| Profile & Organization | 12 | 2 | 0 | 10 | 0 |
| Leave Management | 22 | 0 | 0 | 22 | 8 |
| Documents | 12 | 0 | 0 | 12 | 0 |
| Error Handling | 12 | 0 | 0 | 12 | 0 |
| **TOTAL** | **62** | **6** | **0** | **56** | **8** |

---

## Staging Data Requirements

### Required Before Extended Testing

| Data | Status | Notes |
|------|--------|-------|
| Employee records | ✅ Ready | 97 employees |
| PTO allocations | ✅ Ready | 25 days for 2026 |
| Sick Leave allocation | ❌ Not configured | 10 days needed |
| Unpaid Leave type | ❌ Not configured | Enable in Odoo |
| Public Holidays 2026 | ❌ Not configured | CZ/company holidays |
| HR Documents | ✅ Ready | 5 docs in 2 categories |

---

## Test Execution Summary

### Setup Tests (S01-S04)

| ID | Name | Status | Result |
|----|------|--------|--------|
| S01 | Verify Login | ✅ Pass | User logged in as jiri.manas@keboola.com |
| S02 | Add MCP Server | ✅ Pass | Odoo MCP Staging connector present in org |
| S03 | OAuth Connect | ✅ Pass | Google OAuth flow completed, redirect_uri fixed |
| S04 | Verify Tools | ✅ Pass | MCP tools available (Configure button visible) |

### Profile Tests (P01-P12)

| ID | Name | Tool | Status | Result |
|----|------|------|--------|--------|
| P01 | Get My Profile | get_my_profile | ✅ Pass | Name: Jiri Manas, Title: CTO, Dept: Leadership, Division: Operations, Email: jiri.manas@keboola.com, Phone: +420 724 253 175, Manager: Pavel Doležal, Coach: Pavel Doležal |
| P02 | Get My Manager | get_my_manager | ✅ Pass | Name: Pavel Doležal, Title: Co-Founder and CEO, Dept: Leadership, Email: pavel.dolezal@keboola.com, Phone: +602 654 654 |
| P03 | Get My Team | get_my_team | ⏳ Slow | Request timed out due to server latency (~60s+) |
| P04 | Find Colleague | find_colleague | ⏳ Pending | - |
| P05 | Find by Department | search_employees | ⏳ Pending | - |
| P06 | Get Direct Reports | get_direct_reports | ⏳ Pending | - |
| P07 | Update Contact | update_my_contact | ⏳ Pending | - |
| P08 | Search Directory | search_employees | ⏳ Pending | - |
| P09 | Custom Fields | get_my_profile | ⏳ Pending | - |
| P10 | Coach Info | get_my_profile | ⏳ Pending | - |
| P11 | Find All Managers | search_records | ⏳ Pending | - |
| P12 | Revert Contact | update_my_contact | ⏳ Pending | - |

### Leave Tests (L01-L22)

| ID | Name | Tool | Status | Requires Staging |
|----|------|------|--------|------------------|
| L01 | Get Leave Balance | get_my_leave_balance | ⏳ Pending | - |
| L02 | Specific Balance (Sick) | get_my_leave_balance | ⏳ Pending | Sick leave |
| L03 | Leave History | get_my_leave_requests | ⏳ Pending | - |
| L04 | Pending Leave | get_my_leave_requests | ⏳ Pending | - |
| L05 | Upcoming Leave | get_my_leave_requests | ⏳ Pending | - |
| L06 | Request Vacation | request_leave | ⏳ Pending | - |
| L07 | Request Sick | request_leave | ⏳ Pending | Sick leave |
| L08 | Request Half Day | request_leave | ⏳ Pending | - |
| L09 | Cancel Leave | cancel_leave_request | ⏳ Pending | - |
| L10 | Team Availability | search_holidays | ⏳ Pending | - |
| L11 | Public Holidays | get_public_holidays | ⏳ Pending | Holidays |
| L12 | Leave with Reason | request_leave | ⏳ Pending | - |
| L13 | Request Unpaid | request_leave | ⏳ Pending | Unpaid leave |
| L14 | All Leave Balances | get_my_leave_balance | ⏳ Pending | - |
| L15 | Sick Same Day | request_leave | ⏳ Pending | Sick leave |
| L16 | Multi-Day Sick | request_leave | ⏳ Pending | Sick leave |
| L17 | Leave Over Holiday | request_leave | ⏳ Pending | Holidays |
| L18 | Holiday in Range | get_public_holidays | ⏳ Pending | Holidays |
| L19 | Year Holidays | get_public_holidays | ⏳ Pending | Holidays |
| L20 | Single Day Leave | request_leave | ⏳ Pending | - |
| L21 | Balance After Request | get_my_leave_balance | ⏳ Pending | - |
| L22 | Multiple Pending | get_my_leave_requests | ⏳ Pending | - |

### Document Tests (D01-D12)

| ID | Name | Tool | Status | Result |
|----|------|------|--------|--------|
| D01 | Document Categories | get_document_categories | ⏳ Pending | - |
| D02 | List All Documents | get_my_documents | ⏳ Pending | - |
| D03 | List Contracts | get_my_documents | ⏳ Pending | - |
| D04 | List Identity Docs | get_my_documents | ⏳ Pending | - |
| D05 | Download Document | download_document | ⏳ Pending | - |
| D06 | Upload Identity | upload_identity_document | ⏳ Pending | - |
| D07 | Document Details | get_document_details | ⏳ Pending | - |
| D08 | Expiring Documents | get_my_documents | ⏳ Pending | - |
| D09 | Upload ID Card | upload_identity_document | ⏳ Pending | - |
| D10 | Upload Driving License | upload_identity_document | ⏳ Pending | - |
| D11 | Document Count | get_document_categories | ⏳ Pending | - |
| D12 | Recent Documents | get_my_documents | ⏳ Pending | - |

### Error Tests (E01-E12)

| ID | Name | Expected Error | Status |
|----|------|----------------|--------|
| E01 | Invalid Employee | "Employee not found" | ⏳ Pending |
| E02 | Overlapping Dates | "Dates overlap" | ⏳ Pending |
| E03 | Insufficient Balance | "Insufficient balance" | ⏳ Pending |
| E04 | Cancel Approved | "Cannot cancel" | ⏳ Pending |
| E05 | Access Denied | "Access denied" | ⏳ Pending |
| E06 | Invalid Dates | "Invalid date" | ⏳ Pending |
| E07 | End Before Start | "End date before start" | ⏳ Pending |
| E08 | Past Date Request | "Past date" error | ⏳ Pending |
| E09 | Invalid Leave Type | "Leave type not found" | ⏳ Pending |
| E10 | Cancel Non-Existent | "Request not found" | ⏳ Pending |
| E11 | Empty Document Upload | "No content" error | ⏳ Pending |
| E12 | Invalid Document Type | "Invalid type" error | ⏳ Pending |

---

## Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Half-day leave | Not supported | Odoo limitation - full days only |
| Leave approval workflow | Read-only | Cannot approve via MCP |
| Document expiry dates | Partial | Depends on Odoo DMS config |

---

## Test Coverage Summary

| Metric | Previous | Current Target |
|--------|----------|----------------|
| Tests Defined | 40 | 62 |
| Tests Executed | 15 | 0 (reset) |
| Coverage % | 37.5% | Target: 100% |
| Leave Types Tested | 1 (PTO) | Target: 3 (PTO, Sick, Unpaid) |
| Error Tests | 0 | Target: 12 |

---

## Execution Notes

**Test execution order:**
1. Setup tests (S01-S04) - ✅ COMPLETED
2. Profile tests (P01-P12) - 🔄 IN PROGRESS (2/12 complete)
3. Leave tests - PTO only (L01, L03-L06, L09, L12, L14, L20-L22)
4. Leave tests - Requires staging (L02, L07, L11, L13, L15-L19)
5. Document tests (D01-D12)
6. Error tests (E01-E12)

**Staging configuration completed:**
1. ✅ Sick Leave allocation - Configured
2. ✅ Unpaid Leave type - Enabled
3. ✅ Public holidays for 2026 - Configured

**Issues Encountered:**
1. **OAuth redirect_uri mismatch** - Fixed by adding `https://claude.ai/api/mcp/auth_callback` to GCP OAuth client
2. **MCP Server Performance** - Tool calls taking 30-60+ seconds, causing timeouts during testing

---

## Test Session Log

### Session 1 - 2026-01-08

**Environment:**
- Claude.ai with Opus 4.5
- Odoo MCP Staging connected via Google OAuth
- Test user: jiri.manas@keboola.com

**Results:**
- S01-S04: All setup tests PASSED
- P01: Get My Profile - PASSED (returned full profile data)
- P02: Get My Manager - PASSED (returned Pavel Doležal info)
- P03: Get My Team - TIMEOUT (server latency issue)

**Next Steps:**
- Investigate MCP server performance issues
- Continue profile tests after server optimization
- Proceed with leave and document tests

---

*Report initialized: 2026-01-04*
*Last updated: 2026-01-08*
*Status: In Progress - Performance issues affecting execution speed*
